.PHONY: build clean install-deps test-packages sync

# Default target
all: build

# Install/sync dependencies
install-deps:
	uv sync --dev

# Sync dependencies only
sync:
	uv sync

# Build all proto packages
build:
	uv run python scripts/build_proto_packages.py

# Clean generated packages
clean:
	@if [ -f "scripts/.env" ]; then \
		. scripts/.env; \
		if [ -n "$$OUTPUT_DIR" ]; then \
			echo "Cleaning $$OUTPUT_DIR"; \
			rm -rf "$$OUTPUT_DIR/packages"; \
		else \
			echo "Cleaning generated_packages"; \
			rm -rf generated_packages; \
		fi; \
	else \
		echo "No .env file found, cleaning generated_packages"; \
		rm -rf generated_packages; \
	fi

# Test package building (dry run)
test:
	uv run python scripts/build_proto_packages.py --dry-run

# Install generated packages for development
install-dev:
	uv pip install -e generated_packages/packages/transcribeclient
	uv pip install -e generated_packages/packages/transcribeserver
	uv pip install -e generated_packages/packages/audiocloneclient
	uv pip install -e generated_packages/packages/audiocloneserver

# Initialize uv project
init:
	uv init --no-readme

# Help target
help:
	@echo "Available targets:"
	@echo "  init          - Initialize uv project"
	@echo "  install-deps  - Install/sync dependencies with uv"
	@echo "  sync          - Sync dependencies only"
	@echo "  build         - Build all proto packages"
	@echo "  clean         - Clean generated packages"
	@echo "  test          - Test package building (dry run)"
	@echo "  install-dev   - Install generated packages in development mode"
	@echo "  help          - Show this help message"
