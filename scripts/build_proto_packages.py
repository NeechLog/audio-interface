#!/usr/bin/env python3
"""
Build script to generate Python packages from proto files.
Generates 5 packages:
- AudioMessages (standalone package with AudioMessage and Metadata)
- TranscribeClient (depends on AudioMessages)
- TranscribeServer (depends on AudioMessages)
- AudioCloneClient (depends on AudioMessages)
- AudioCloneServer (depends on AudioMessages)
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List
from jinja2 import Environment, FileSystemLoader, Template

def load_env_file(env_file_path: str = None) -> None:
    """Load environment variables from a .env file."""
    if env_file_path is None:
        env_file_path = Path(__file__).parent / ".env"
    
    env_path = Path(env_file_path)
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Load environment variables from .env file
load_env_file()

# Configuration
PROTO_DIR = Path(__file__).parent.parent / "proto"
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(Path(__file__).parent.parent / "generated_packages")))
PACKAGES_DIR = OUTPUT_DIR / "packages"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Package definitions
PACKAGES = {
    "AudioMessages": {
        "proto_files": ["audio-message.proto"],
        "type": "messages",
        "description": "Standalone package containing AudioMessage and Metadata protobuf messages"
    },
    "TranscribeClient": {
        "proto_files": ["transcribe-interface.proto"],
        "service": "TranscribeWorker",
        "type": "client",
        "description": "Python client for TranscribeModelWorker service",
        "dependencies": ["AudioMessages"]
    },
    "TranscribeServer": {
        "proto_files": ["transcribe-interface.proto"],
        "service": "TranscribeWorker", 
        "type": "server",
        "description": "Python server skeleton for TranscribeModelWorker service",
        "dependencies": ["AudioMessages"]
    },
    "AudioCloneClient": {
        "proto_files": ["clone-interface.proto"],
        "service": "AudioCloneModelWorker",
        "type": "client",
        "description": "Python client for AudioCloneModelWorker service",
        "dependencies": ["AudioMessages"]
    },
    "AudioCloneServer": {
        "proto_files": ["clone-interface.proto"],
        "service": "AudioCloneModelWorker",
        "type": "server", 
        "description": "Python server skeleton for AudioCloneModelWorker service",
        "dependencies": ["AudioMessages"]
    }
}

def get_template_env() -> Environment:
    """Initialize Jinja2 template environment."""
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True
    )

def run_command(cmd: List[str], cwd: Path = None) -> bool:
    """Run a command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        print(f"Success: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False

def run_uv_command(cmd: List[str], cwd: Path = None) -> bool:
    """Run a uv command and return success status."""
    print(f"Running uv: {' '.join(cmd)}")
    try:
        result = subprocess.run(["uv"] + cmd, cwd=cwd, check=True, capture_output=True, text=True)
        print(f"Success: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False

def create_package_structure(package_name: str, config: dict) -> Path:
    """Create the package directory structure."""
    package_dir = PACKAGES_DIR / package_name.lower()
    package_dir.mkdir(parents=True, exist_ok=True)
    
    # Create package structure
    (package_dir / package_name.lower()).mkdir(exist_ok=True)
    (package_dir / "tests").mkdir(exist_ok=True)
    
    return package_dir

def generate_proto_code(package_dir: Path, package_name: str, config: dict) -> bool:
    """Generate Python code from proto files."""
    module_name = package_name.lower()
    proto_files = [str(PROTO_DIR / f) for f in config["proto_files"]]
    
    # Common grpc command for both messages and service packages
    grpc_cmd = [
        "run", "python", "-m", "grpc_tools.protoc",
        f"--proto_path={PROTO_DIR}",
        f"--python_out={package_dir / module_name}",
        f"--grpc_python_out={package_dir / module_name}",
    ] + proto_files
    
    if not run_uv_command(grpc_cmd):
        return False
    
    # Create __init__.py files
    (package_dir / module_name / "__init__.py").touch()
    
    # Special cleanup for service packages (non-messages)
    if config["type"] != "messages":
        # Remove the generated audio_message_pb2.py files since they'll come from AudioMessages package
        audio_message_pb2 = package_dir / module_name / "audio_message_pb2.py"
        audio_message_pb2_grpc = package_dir / module_name / "audio_message_pb2_grpc.py"
        
        if audio_message_pb2.exists():
            audio_message_pb2.unlink()
        if audio_message_pb2_grpc.exists():
            audio_message_pb2_grpc.unlink()
        
        # Fix the imports in the generated pb2 files to use audiomessages package
        for pb2_file in (package_dir / module_name).glob("*_pb2.py"):
            content = pb2_file.read_text()
            # Replace the import statement to use audiomessages package
            content = content.replace(
                'import audio_message_pb2 as audio__message__pb2',
                'import audiomessages.audio_message_pb2 as audio__message__pb2'
            )
            pb2_file.write_text(content)
    
    return True

def create_client_wrapper(package_dir: Path, package_name: str, config: dict) -> bool:
    """Create client wrapper code using templates."""
    env = get_template_env()
    module_name = package_name.lower()
    service_name = config["service"]
    
    # Load main client template
    client_template = env.get_template("grpc_client_wrapper.py.j2")
    
    # Load service-specific methods template
    if "Transcribe" in package_name:
        methods_template = env.get_template("transcribe_client_methods.py.j2")
        service_methods = methods_template.render(service_name=service_name)
    elif "Clone" in package_name:
        methods_template = env.get_template("clone_client_methods.py.j2")
        service_methods = methods_template.render(service_name=service_name)
    else:
        service_methods = ""
    
    # Add proper indentation to service methods
    if service_methods:
        indented_methods = "\n".join(f"    {line}" if line.strip() else line for line in service_methods.split("\n"))
    else:
        indented_methods = ""
    
    # Render main client template
    client_code = client_template.render(
        description=config['description'],
        module_name=module_name,
        service_name=service_name,
        package_name=package_name,
        service_methods=indented_methods
    )
    
    client_file = package_dir / module_name / "client.py"
    client_file.write_text(client_code)
    
    return True

def create_server_skeleton(package_dir: Path, package_name: str, config: dict) -> bool:
    """Create server skeleton code using templates."""
    env = get_template_env()
    module_name = package_name.lower()
    service_name = config["service"]
    
    # Load main server template
    server_template = env.get_template("grpc_server_skeleton.py.j2")
    
    # Load service-specific methods template
    if "Transcribe" in package_name:
        methods_template = env.get_template("transcribe_server_methods.py.j2")
        service_methods = methods_template.render(service_name=service_name)
    elif "Clone" in package_name:
        methods_template = env.get_template("clone_server_methods.py.j2")
        service_methods = methods_template.render(service_name=service_name)
    else:
        service_methods = ""
    
    # Add proper indentation to service methods
    if service_methods:
        indented_methods = "\n".join(f"    {line}" if line.strip() else line for line in service_methods.split("\n"))
    else:
        indented_methods = ""
    
    # Render main server template
    server_code = server_template.render(
        description=config['description'],
        module_name=module_name,
        service_name=service_name,
        service_methods=indented_methods,
        proto_file_name=config["proto_files"][0].replace('.proto', '_pb2').replace('-', '_')
    )
    
    server_file = package_dir / module_name / "server.py"
    server_file.write_text(server_code)
    
    return True

def create_setup_py(package_dir: Path, package_name: str, config: dict) -> bool:
    """Create pyproject.toml for the package using templates."""
    env = get_template_env()
    module_name = package_name.lower()
    
    # Base dependencies for all packages
    base_dependencies = [
        "grpcio>=1.50.0",
        "grpcio-tools>=1.50.0", 
        "protobuf>=4.0.0",
    ]
    
    # Add AudioMessages dependency for service packages as local path
    if config.get("dependencies"):
        # Calculate absolute path to audiomessages package for proper dependency specification
        audio_messages_path = PACKAGES_DIR / "audiomessages"
        # Use local path format for dependency
        base_dependencies.append(f"audiomessages @ {audio_messages_path.as_uri()}")
    
    # Special handling for AudioMessages package - it doesn't need grpcio-tools
    if config["type"] == "messages":
        dependencies = ["protobuf>=4.0.0"]
    else:
        dependencies = base_dependencies
    
    # Load and render pyproject template
    pyproject_template = env.get_template("python_package_config.toml.j2")
    pyproject_content = pyproject_template.render(
        description=config['description'],
        package_name=package_name,
        module_name=module_name,
        dependencies=dependencies
    )
    
    pyproject_file = package_dir / "pyproject.toml"
    pyproject_file.write_text(pyproject_content)
    
    return True

def create_server_launcher(package_dir: Path, package_name: str, config: dict) -> bool:
    """Create server launcher library using templates."""
    env = get_template_env()
    
    # Load server launcher template
    launcher_template = env.get_template("grpc_server_launcher.py.j2")
    launcher_code = launcher_template.render()
    
    # Create launcher module
    launcher_dir = package_dir / package_name.lower() / "grpc_server_launcher.py"
    launcher_dir.write_text(launcher_code)
    
    # Create server usage example with launcher
    example_template = env.get_template("server_with_launcher_example.py.j2")
    module_name = package_name.lower()
    service_name = config["service"]
    
    example_code = example_template.render(
        description=config['description'],
        module_name=module_name,
        service_name=service_name,
        package_name=package_name,
        proto_file_name=config["proto_files"][0].replace('.proto', '_pb2_grpc').replace('-', '_')
    )
    
    example_file = package_dir / package_name.lower() / "server_example.py"
    example_file.write_text(example_code)
    
    return True

def create_readme(package_dir: Path, package_name: str, config: dict) -> bool:
    """Create README.md for the package using templates."""
    env = get_template_env()
    
    # Load main README template
    readme_template = env.get_template("package_readme.md.j2")
    
    # Load usage example template based on package type
    if config["type"] == "messages":
        usage_template = env.get_template("messages_usage_example.md.j2")
        usage_examples = usage_template.render(package_name=package_name)
    elif "Client" in package_name:
        usage_template = env.get_template("client_usage_example.md.j2")
        usage_examples = usage_template.render(package_name=package_name)
    elif "Server" in package_name:
        usage_template = env.get_template("server_usage_example.md.j2")
        module_name = package_name.lower()
        service_name = config["service"]
        usage_examples = usage_template.render(
            package_name=package_name,
            module_name=module_name,
            service_name=service_name
        )
    else:
        usage_examples = ""
    
    # Render main README template
    readme_content = readme_template.render(
        package_name=package_name,
        description=config['description'],
        usage_examples=usage_examples
    )
    
    readme_file = package_dir / "README.md"
    readme_file.write_text(readme_content)
    
    return True

def build_package(package_name: str, config: dict) -> bool:
    """Build a single package."""
    print(f"\nBuilding package: {package_name}")
    
    # Create package structure
    package_dir = create_package_structure(package_name, config)
    
    # Generate proto code
    if not generate_proto_code(package_dir, package_name, config):
        return False
    
    # Create wrapper code (only for client/server packages, not messages package)
    if config["type"] == "client":
        if not create_client_wrapper(package_dir, package_name, config):
            return False
    elif config["type"] == "server":
        if not create_server_skeleton(package_dir, package_name, config):
            return False
        if not create_server_launcher(package_dir, package_name, config):
            return False
    elif config["type"] == "messages":
        # For AudioMessages package, create __init__.py using template
        env = get_template_env()
        module_name = package_name.lower()
        
        # Load and render messages init template
        init_template = env.get_template("messages_package_init.py.j2")
        init_content = init_template.render()
        
        init_file = package_dir / module_name / "__init__.py"
        init_file.write_text(init_content)
    
    # Create pyproject.toml
    if not create_setup_py(package_dir, package_name, config):
        return False
    
    # Create README
    if not create_readme(package_dir, package_name, config):
        return False
    
    print(f"Successfully built {package_name}")
    return True

def main():
    """Main build function."""
    print("Starting proto package build process...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    PACKAGES_DIR.mkdir(exist_ok=True)
    
    # Build all packages
    success_count = 0
    for package_name, config in PACKAGES.items():
        if build_package(package_name, config):
            success_count += 1
        else:
            print(f"Failed to build {package_name}")
    
    print(f"\\nBuild complete: {success_count}/{len(PACKAGES)} packages built successfully")
    
    if success_count == len(PACKAGES):
        print("\\nAll packages built successfully!")
        print(f"Packages available in: {PACKAGES_DIR}")
        print("\\nTo install packages:")
        for pkg_name in PACKAGES.keys():
            print(f"  uv add --editable {PACKAGES_DIR / pkg_name.lower()}")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
