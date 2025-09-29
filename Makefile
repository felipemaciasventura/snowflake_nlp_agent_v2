# Makefile for Snowflake NLP Agent v2

.PHONY: help install install-dev test lint format type-check clean run build docs setup-dev

# Default target
help:
	@echo "Available commands:"
	@echo "  install       - Install production dependencies"
	@echo "  install-dev   - Install development dependencies"
	@echo "  setup-dev     - Complete development environment setup"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linting (flake8)"
	@echo "  format        - Format code (black)"
	@echo "  type-check    - Run type checking (mypy)"
	@echo "  clean         - Clean up build artifacts"
	@echo "  run           - Run the Streamlit application"
	@echo "  build         - Build the package"
	@echo "  docs          - Generate documentation"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,test,docs]"

setup-dev: install-dev
	pre-commit install
	@echo "Development environment setup complete!"

# Testing
test:
	pytest tests/ -v --cov=src --cov-report=term-missing

test-fast:
	pytest tests/ -v -x --disable-warnings

# Code quality
lint:
	flake8 src/ streamlit_app.py tests/

format:
	black src/ streamlit_app.py tests/
	isort src/ streamlit_app.py tests/

type-check:
	mypy src/ streamlit_app.py

quality: format lint type-check
	@echo "Code quality checks complete!"

# Development
run:
	streamlit run streamlit_app.py

run-debug:
	DEBUG=True streamlit run streamlit_app.py

# Build and deployment
build:
	python -m build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Documentation
docs:
	mkdocs serve

docs-build:
	mkdocs build

# Verification
verify: clean format lint type-check test
	@echo "All verification checks passed!"

# Environment setup
env-example:
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from template"; else echo ".env already exists"; fi

# Project initialization
init: env-example setup-dev
	@echo "Project initialization complete!"
	@echo "Next steps:"
	@echo "1. Edit .env with your credentials"
	@echo "2. Run 'make run' to start the application"