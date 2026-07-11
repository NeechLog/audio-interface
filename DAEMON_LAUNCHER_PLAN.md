# Daemon Launcher Fix Plan

## Context

`audio-interface` generates the shared gRPC server launcher from
`scripts/templates/grpc_server_launcher.py.j2` during `build_proto_packages`.
Generated server packages, including `audiocloneserver`, inherit this launcher.

The current daemon path can construct the service implementation before the
process is daemonized. That is risky for model-backed services such as
Qwen/Torch/CUDA workers because initialized model, GPU, thread, or file-handle
state may not survive daemon detach/fork cleanly. The symptom is:

- `uv run qwen3ttsvaserver-start --daemon` returns after startup logging.
- No process is listening on the configured gRPC port.
- No `qwen3` process is visible in `ps`.

## Problem Area

The single-process daemon branch in `start_grpc_server` constructs the service
before entering `GrpcServerLauncher.start_server`:

```python
if daemon:
    launcher.start_server(
        service_add_func,
        service_class(*service_init_args, **(service_init_kwargs or {})),
    )
```

`start_server` then daemonizes around `_run_server_core`, but the service object
has already been created in the parent process.

The multi-process helper already has a better lifecycle shape. It wraps
`run_logic` in `_run_as_daemon` first, and `run_logic` creates the service
instance after daemonization.

## Proposed Approach

Update `scripts/templates/grpc_server_launcher.py.j2` so all server starts go
through `GrpcServerLauncher.create_multi_process_server`, including
single-process foreground starts.

That helper already has the right lifecycle shape:

- If daemon mode is enabled, daemonization wraps `run_logic`.
- `run_logic` constructs the service after daemonization.
- If `num_processes <= 1`, `run_logic` still runs a normal single-process
  server.
- If `num_processes > 1`, it starts worker processes as before.

`start_grpc_server` can therefore drop the special-case branching and always
delegate to the helper:

```python
GrpcServerLauncher.create_multi_process_server(
    config,
    service_add_func,
    service_class,
    service_init_args,
    service_init_kwargs,
)
```

This removes duplicate lifecycle logic and ensures the service is constructed
in the same place for every mode. Foreground single-process behavior should stay
functionally unchanged, but it now uses the shared `run_logic` path.

## Additional Cleanup

Normalize daemon log and PID paths before entering `DaemonContext`.

The launcher defaults `working_dir` to `/`, and daemon context changes into that
directory. Relative log paths such as `qwen3ttsvaserver.log` can therefore end up
under `/` instead of the caller's current directory.

Recommended handling:

- Convert `pid_file` to an absolute path before creating `TimeoutPIDLockFile`.
- Convert `log_file` to an absolute path before daemonization, or set
  `working_dir` to the current directory when building the default config.
- Keep the generated CLI examples passing explicit `--log-file` and
  `--pid-file` paths where appropriate.

## Validation Plan

1. Update `scripts/templates/grpc_server_launcher.py.j2`.
2. Run `make build` from `audio-interface`.
3. Confirm generated launcher output under `/Users/gagan/projects/work/packages`
   reflects the template change.
4. Run `make test-packages`.
5. In `Qwen3TTSVAServer`, refresh/sync the editable generated package if needed.
6. Start foreground once:

   ```bash
   uv run qwen3ttsvaserver-start --log-level DEBUG
   ```

7. Start daemon mode with explicit paths:

   ```bash
   uv run qwen3ttsvaserver-start --daemon \
     --pid-file "$(pwd)/qwen3ttsvaserver.pid" \
     --log-file "$(pwd)/qwen3ttsvaserver.log"
   ```

8. Verify the daemon:

   ```bash
   cat qwen3ttsvaserver.pid
   ps -fp "$(cat qwen3ttsvaserver.pid)"
   ss -ltnp | grep 50053
   tail -200 qwen3ttsvaserver.log
   ```

9. Stop it:

   ```bash
   uv run qwen3ttsvaserver-stop --pid-file "$(pwd)/qwen3ttsvaserver.pid"
   ```

## Expected Outcome

Daemon mode creates the service and loads model state only inside the daemon
child process. The parent process exits after daemon setup, while the child keeps
the gRPC port open and writes logs/PID files to predictable paths.

## Addendum: Strategy Change

After testing the daemon path with Qwen on macOS, the original `python-daemon`
approach exposed a deeper platform issue:

```text
+[MPSGraphObject initialize] may have been in progress in another thread when fork() was called.
We cannot safely call it or ignore it in the fork() child process. Crashing instead.
```

This means the remaining problem is not just service construction order inside
`start_grpc_server`. The fork-based daemon mechanism itself is unsafe for model
runtimes that may touch Objective-C, MPS, Metal, Torch, gRPC threads, or similar
native state before daemonization.

The revised strategy is:

- Put daemon/PID/log handling in a reusable generated utility.
- Make service repo entrypoints call that utility before importing the service
  app.
- If daemon mode is requested, spawn a detached fresh Python child with
  `--daemon` removed and `GRPC_DAEMON=false`.
- The parent writes the child PID and exits.
- The child imports the service app and starts the server in normal foreground
  mode.
- If daemon mode is not requested, the utility imports the service app directly
  and runs it in the current process.

This avoids inheriting partially initialized native runtime state across `fork`.
It also ensures model loading happens only in the long-lived server child, not
in the daemon launcher parent.

## Addendum: Updated Ownership

The revised split is:

- `scripts/templates/grpc_server_launcher.py.j2`
  - Owns reusable daemon utilities.
  - Owns stale PID handling.
  - Owns detached child process spawning.
  - Owns lazy service app import via an import string.
  - Keeps `start_grpc_server` as a foreground gRPC lifecycle helper.

- Service repo entrypoints
  - Own service-specific import path and defaults.
  - Must not import model-heavy app modules before daemon handling.
  - Call `run_service_entrypoint(...)` with an app import string.

- Service app modules
  - Own service wiring, handlers, and model initialization.
  - Should not own daemon process management.

## Addendum: Implemented Shape

The generated server launcher now exposes:

```python
run_service_entrypoint(
    app_main_import="app:main",
    injected_command="start",
    default_log_file="qwen3ttsvaserver.log",
    default_pid_file="qwen3ttsvaserver.pid",
)
```

Important detail: `app_main_import` is a string. The helper imports that module
only after daemon handling has completed. Passing an already imported function
would recreate the same early-import problem.

For Qwen:

```python
from audiocloneserver.grpc_server_launcher import run_service_entrypoint


def main_wrapper() -> None:
    run_service_entrypoint(
        app_main_import="app:main",
        injected_command="start",
        default_log_file="qwen3ttsvaserver.log",
        default_pid_file="qwen3ttsvaserver.pid",
    )
```

For Parakeet:

```python
from transcribeserver.grpc_server_launcher import run_service_entrypoint


def main():
    run_service_entrypoint(
        app_main_import="parakeettranscriptvaserver.app:run",
        default_log_file="parakeet_server.log",
        default_pid_file="transcribeserver.pid",
    )
```

This matters especially for Parakeet because its app module eagerly constructs
and loads the transcription model at import time.

## Addendum: Spawn-Based Daemon Flow

The daemon flow is now:

```text
service-start --daemon
  -> lightweight entrypoint imports only generated helper
  -> helper validates/removes stale PID file
  -> helper spawns detached child:
       same Python executable
       same argv with --daemon removed
       GRPC_DAEMON=false
       AUDIOCLONESERVER_DAEMON_CHILD=1
       stdout/stderr appended to log file
  -> parent writes child PID
  -> parent exits

child process
  -> entrypoint runs again without daemon mode
  -> helper imports app module from app_main_import string
  -> app starts foreground gRPC server
  -> model/native runtime initializes only in child
```

`start_grpc_server(..., daemon=True)` also falls back to the same spawn helper.
That path is retained for callers that bypass the service entrypoint, but the
preferred path is still daemon handling before app import.

## Addendum: Current Validation

Validation performed after the strategy change:

```text
make build
5/5 packages built successfully

make test-packages
Ran 3 tests in 0.000s
OK
```

Additional checks:

- Confirmed generated `audiocloneserver` and `transcribeserver` expose
  `spawn_daemon_child` and `run_service_entrypoint`.
- Confirmed Qwen `start_server.py` imports without importing `app.py`.
- Confirmed Parakeet `main.py` imports without importing
  `parakeettranscriptvaserver.app`.
- Smoke-tested a detached child with a tiny temp app; parent returned, wrote a
  PID, and the child wrote `child reached`.

Parakeet full `uv run` verification was not completed because dependency
resolution selected Python 3.14 while `kaldialign` only had a `cp313` wheel in
that environment. The lightweight import verification still confirmed the
daemon-entrypoint boundary change.
