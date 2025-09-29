# Contributing to Snowflake NLP Agent v2

## 🎯 Overview

We welcome contributions to the Snowflake NLP Agent v2! This document provides guidelines for contributing to this project.

## 🚀 Quick Start for Contributors

### 1. Environment Setup

```bash
# Fork and clone the repository
git clone https://github.com/your-username/snowflake_nlp_agent_v2.git
cd snowflake_nlp_agent_v2

# Complete development environment setup
make init
```

### 2. Development Workflow

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ...

# Run quality checks
make quality          # Format, lint, and type-check
make test            # Run tests with coverage

# Commit your changes
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

## 📋 Development Standards

### Code Quality Requirements

All contributions must meet these standards:

- **✅ Code Formatting**: Black formatter (88 character limit)
- **✅ Linting**: flake8 compliance with project configuration
- **✅ Type Hints**: mypy type checking (encouraged)
- **✅ Testing**: Unit tests for new features
- **✅ Documentation**: Docstrings and README updates

### Available Commands

```bash
# Quality assurance
make format          # Format code with Black
make lint            # Check code style with flake8  
make type-check      # Type checking with mypy
make quality         # Run all quality checks

# Testing
make test            # Run full test suite with coverage
make test-fast       # Quick test run without coverage

# Development
make run             # Start application
make run-debug       # Start with debug logging
make clean           # Clean build artifacts
```

## 🧪 Testing Guidelines

### Writing Tests

1. **Location**: Place tests in the `tests/` directory
2. **Naming**: Test files should be named `test_*.py`
3. **Structure**: Use pytest fixtures from `tests/conftest.py`
4. **Coverage**: Maintain test coverage above 80%

### Example Test

```python
import pytest
from src.utils.config import Config

def test_config_initialization():
    """Test that Config can be initialized."""
    config = Config()
    assert config is not None

def test_config_with_mock_env(mock_snowflake_connection):
    """Test Config with mocked environment."""
    # Use fixtures from conftest.py
    assert mock_snowflake_connection.is_connected
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage report
pytest --cov=src --cov-report=html
```

## 🔄 Pull Request Process

### 1. Pre-submission Checklist

- [ ] Code passes all quality checks (`make quality`)
- [ ] Tests pass (`make test`)
- [ ] Documentation updated (README, docstrings)
- [ ] CHANGELOG.md updated (if significant change)
- [ ] Conventional commit messages used

### 2. PR Requirements

- **Clear Description**: Explain what changes and why
- **Test Coverage**: Include tests for new functionality
- **Documentation**: Update relevant documentation
- **No Breaking Changes**: Unless discussed in an issue first

### 3. Review Process

1. **Automated Checks**: CI/CD pipeline runs automatically
2. **Code Review**: Maintainer review required
3. **Testing**: Verify functionality works as expected
4. **Merge**: Squash and merge preferred

## 🏗️ Project Architecture

### Directory Structure

```
src/
├── agent/           # NLP processing logic
├── database/        # Database connections
├── utils/           # Utilities and configuration
└── prompts/         # SQL prompt templates

tests/
├── conftest.py      # Test fixtures
├── test_*.py        # Test modules
└── __init__.py      # Test package init
```

### Key Components

- **NLP Agent**: `src/agent/nlp_agent.py` - Core LLM integration
- **Database**: `src/database/snowflake_conn.py` - Snowflake connectivity
- **Configuration**: `src/utils/config.py` - Environment configuration
- **UI**: `streamlit_app.py` - Web interface

## 🐛 Bug Reports

### Before Reporting

1. Check existing issues
2. Verify with latest version
3. Test with minimal example

### Report Template

```markdown
**Bug Description**
A clear description of the bug.

**Steps to Reproduce**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What should happen.

**Actual Behavior**
What actually happened.

**Environment**
- Python version:
- OS:
- Package version:
```

## 💡 Feature Requests

### Process

1. **Check Issues**: See if feature already requested
2. **Create Issue**: Use feature request template
3. **Discuss**: Engage with maintainers
4. **Implement**: Submit PR after approval

### Feature Template

```markdown
**Feature Description**
Clear description of the proposed feature.

**Use Case**
Why this feature would be useful.

**Implementation Ideas**
Suggestions for how to implement.

**Alternatives**
Other ways to achieve the same goal.
```

## 🔐 Security

### Reporting Security Issues

- **Do not** create public issues for security vulnerabilities
- **Email**: [security@project.com] with details
- **Response**: We'll respond within 48 hours

### Security Guidelines

- Never commit credentials or secrets
- Use environment variables for sensitive data
- Follow secure coding practices
- Keep dependencies updated

## 📚 Documentation

### Documentation Standards

- **README.md**: Keep updated with new features
- **Docstrings**: Follow Google style
- **Comments**: Explain complex logic
- **Examples**: Include usage examples

### Building Documentation

```bash
# Local documentation server
make docs

# Build documentation
make docs-build
```

## 🌟 Recognition

Contributors will be recognized in:

- **CHANGELOG.md**: Feature additions and bug fixes
- **README.md**: Major contributors section
- **Release Notes**: Significant contributions

## 📞 Getting Help

- **Issues**: GitHub issues for bugs and features
- **Discussions**: GitHub discussions for questions
- **Email**: [maintainer@project.com] for direct contact

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Snowflake NLP Agent v2!** 🚀