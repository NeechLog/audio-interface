 # Audio Interface

Proto definitions and generated Python packages for audio inference services.

## Overview

This project contains protobuf definitions for audio processing services and a build system that generates 4 independent Python packages:

- **TranscribeClient** - Python client for TranscribeModelWorker service
- **TranscribeServer** - Python server skeleton for TranscribeModelWorker service  
- **AudioCloneClient** - Python client for AudioCloneModelWorker service
- **AudioCloneServer** - Python server skeleton for AudioCloneModelWorker service

## Services

### TranscribeWorker
- Unary transcription: `Transcribe(TranscribeRequest) -> TranscribeResponse`
- Streaming transcription: `StreamTranscription(stream TranscribeRequest) -> stream TranscribeResponse`

### AudioCloneModelWorker  
- Unary cloning: `Clone(CloneRequest) -> CloneResponse`
- Streaming cloning: `StreamClone(stream CloneRequest) -> stream CloneResponse`

## Build System

### Prerequisites

This project uses `uv` for package management and dependency management.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --dev
```

### Building Packages

```bash
# Using Makefile (recommended)
make build

# Or directly with uv
uv run python scripts/build_proto_packages.py
```

This generates 4 packages in `generated_packages/packages/`:
- `transcribeclient/` - Client library for transcription service
- `transcribeserver/` - Server skeleton for transcription service
- `audiocloneclient/` - Client library for audio cloning service
- `audiocloneserver/` - Server skeleton for audio cloning service

### Package Structure

Each generated package includes:
- Generated protobuf Python code (`*_pb2.py`, `*_pb2_grpc.py`)
- Client wrapper (`client.py`) or server skeleton (`server.py`)
- `pyproject.toml` for installation (using hatchling build backend)
- `README.md` with usage examples

### Installing Generated Packages

```bash
# Install individual packages using uv
uv add --editable generated_packages/packages/transcribeclient
uv add --editable generated_packages/packages/transcribeserver
uv add --editable generated_packages/packages/audiocloneclient
uv add --editable generated_packages/packages/audiocloneserver

# Or install in development mode using make
make install-dev
```

## Usage Examples

### Client Usage

```python
from transcribeclient import TranscribeClient

# Create client
with TranscribeClient("localhost:50051") as client:
    # Use client methods
    response = client.transcribe(request)
```

### Server Usage

```python
from transcribeserver.server import serve

# Start server
serve(port=50051)
```

## Git Repository Setup

To publish packages to git repositories:

```bash
# Setup git repositories (update URLs in script first)
uv run python scripts/setup_git_repos.py

# Push to remote
cd generated_packages/packages/transcribeclient
git push -u origin main
```

## Adding New Fields or Messages

This section describes how to modify protobuf definitions and regenerate packages.

### Adding New Fields to Existing Messages

1. **Edit the proto file** in `proto/` directory:
   ```protobuf
   message AudioMessage {
     // Existing fields...
     optional string text = 1;
     optional bytes audio_binary = 2;
     
     // Add new field
     optional string new_field = 8;  // Use next available number
   }
   ```

2. **Update templates** if the new field should be exported:
   - Edit `scripts/templates/messages_package_init.py.j2` to include the new message type
   - Update usage examples in `scripts/templates/messages_usage_example.md.j2`

3. **Regenerate packages**:
   ```bash
   make clean
   make build
   ```

### Adding New Message Types

1. **Define the new message** in the appropriate proto file:
   ```protobuf
   message NewMessage {
     string field1 = 1;
     int32 field2 = 2;
   }
   ```

2. **Update the AudioMessages package template**:
   - Edit `scripts/templates/messages_package_init.py.j2`
   - Add the new message to imports and `__all__` list

3. **Update client/server templates** if needed:
   - Edit `scripts/templates/grpc_client_wrapper.py.j2`
   - Edit `scripts/templates/grpc_server_skeleton.py.j2`
   - Update usage examples in `scripts/templates/messages_usage_example.md.j2`

4. **Update build script description**:
   - Edit `scripts/build_proto_packages.py` to reflect new message types

5. **Regenerate packages**:
   ```bash
   make clean
   make build
   ```

### Important Notes

- **Field numbers**: Always use the next available number when adding fields
- **Backward compatibility**: Use `optional` for new fields to maintain compatibility
- **Template updates**: Remember to update all relevant templates when adding new message types
- **Package rebuild**: Always run `make clean && make build` after proto changes
- **Dependency updates**: Projects using the packages may need to update their imports

### Example: Adding ProcessingMetadata and AudioMessageInfo

Recent changes demonstrate this process:
1. Added `ProcessingMetadata` and `AudioMessageInfo` to `audiomessages/audio_message.proto`
2. Updated `messages_package_init.py.j2` to export the new messages
3. Updated all client/server templates to import the new messages
4. Rebuilt all packages to apply changes

## Using Packages in Other Projects

Add to your project's `pyproject.toml`:

```toml
[project.dependencies]
transcribeclient = {{git = "https://github.com/your-org/transcribe-client.git"}}
transcribeserver = {{git = "https://github.com/your-org/transcribe-server.git"}}
audiocloneclient = {{git = "https://github.com/your-org/audio-clone-client.git"}}
audiocloneserver = {{git = "https://github.com/your-org/audio-clone-server.git"}}
```

Then install with uv:

```bash
uv sync
```

### Development Commands

```bash
# Install dependencies
make install-deps

# Sync dependencies only
make sync

# Build packages
make build

# Clean build
make clean
make build

# Install generated packages in development mode
make install-dev

# Show help
make help
```

### Project Structure

```
audio-interface/
├── proto/                          # Protobuf definitions
│   ├── audiomessages/
│   │   └── audio_message.proto
│   ├── transcribe-interface.proto
│   └── clone-interface.proto
├── scripts/                        # Build and setup scripts
│   ├── build_proto_packages.py
│   └── setup_git_repos.py
├── generated_packages/             # Generated packages (output)
│   └── packages/
│       ├── transcribeclient/
│       ├── transcribeserver/
│       ├── audiocloneclient/
│       └── audiocloneserver/
├── pyproject.toml                  # Project configuration and dependencies
├── Makefile                        # Build commands
└── README.md                       # This file
```

## Dependencies

- Python 3.8+
- uv (package manager)
- grpcio >= 1.50.0
- grpcio-tools >= 1.50.0  
- protobuf >= 4.0.0
- hatchling (build backend)

## License

MIT License - see LICENSE file for details.
