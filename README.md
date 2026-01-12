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
│   ├── audio-message.proto
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

