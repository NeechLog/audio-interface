#!/usr/bin/env python3
"""
Setup script to initialize git repositories for the generated packages.
This script helps prepare the packages for publishing to git repositories.
"""

import os
import subprocess
from pathlib import Path

# Configuration
PACKAGES_DIR = Path(__file__).parent.parent / "generated_packages" / "packages"

# Package repositories (update with your actual git URLs)
PACKAGE_REPOS = {
    "transcribeclient": "git@github.com:your-org/transcribe-client.git",
    "transcribeserver": "git@github.com:your-org/transcribe-server.git", 
    "audiocloneclient": "git@github.com:your-org/audio-clone-client.git",
    "audiocloneserver": "git@github.com:your-org/audio-clone-server.git"
}

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        print(f"Success: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.strip()}")
        return False

def setup_git_repo(package_name: str, repo_url: str) -> bool:
    """Initialize git repository for a package."""
    package_dir = PACKAGES_DIR / package_name
    
    if not package_dir.exists():
        print(f"Package directory {package_dir} does not exist")
        return False
    
    print(f"\nSetting up git repo for {package_name}")
    
    # Initialize git repo
    if not run_command(["git", "init"], cwd=package_dir):
        return False
    
    # Add all files
    if not run_command(["git", "add", "."], cwd=package_dir):
        return False
    
    # Initial commit
    if not run_command(["git", "commit", "-m", "Initial commit - generated from proto files"], cwd=package_dir):
        return False
    
    # Add remote origin
    if not run_command(["git", "remote", "add", "origin", repo_url], cwd=package_dir):
        return False
    
    print(f"Git repository setup complete for {package_name}")
    print(f"To push to remote: cd {package_dir} && git push -u origin main")
    
    return True

def create_gitignore(package_dir: Path) -> bool:
    """Create .gitignore file for the package."""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# uv
.venv/
uv.lock

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
    
    gitignore_file = package_dir / ".gitignore"
    gitignore_file.write_text(gitignore_content)
    return True

def main():
    """Main setup function."""
    print("Setting up git repositories for generated packages...")
    
    success_count = 0
    
    for package_name, repo_url in PACKAGE_REPOS.items():
        package_dir = PACKAGES_DIR / package_name
        
        # Create .gitignore
        if package_dir.exists():
            create_gitignore(package_dir)
        
        # Setup git repo
        if setup_git_repo(package_name, repo_url):
            success_count += 1
        else:
            print(f"Failed to setup git repo for {package_name}")
    
    print(f"\nSetup complete: {success_count}/{len(PACKAGE_REPOS)} repositories setup successfully")
    
    if success_count == len(PACKAGE_REPOS):
        print("\nAll repositories setup successfully!")
        print("\nNext steps:")
        print("1. Create the actual git repositories on GitHub/GitLab")
        print("2. Update the repo URLs in this script with your actual URLs")
        print("3. Run: python3 scripts/setup_git_repos.py")
        print("4. Push each package: cd generated_packages/packages/<package> && git push -u origin main")
        print("5. Update your project's pyproject.toml or requirements.txt to use the git URLs")
    else:
        exit(1)

if __name__ == "__main__":
    main()
