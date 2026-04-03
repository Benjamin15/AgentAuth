# Contributing to AgentAuth

First off, thank you for considering contributing to AgentAuth! It's people like you that make AgentAuth such a great tool.

## How Can I Contribute?

### Reporting Bugs
Before creating bug reports, please check the existing issues to see if the problem has already been reported. When you are creating a bug report, please include as many details as possible.

### Suggesting Enhancements
Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please provide a clear and descriptive title and a small summary of why this enhancement would be useful.

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints and passes type checks.

## Styleguides

### Git Commit Messages
* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

### Python Styleguide
We use `ruff` for linting and formatting, and `mypy` for static type checking.
* Line length is 100 characters.
* Use type hints for all function signatures.

## Setup for Development

```bash
# Clone the repository
git clone https://github.com/Benjamin15/AgentAuth
cd AgentAuth

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -e ".[test]"

# Install pre-commit hooks
pre-commit install
```

## Running Quality Gates

Before submitting a PR, please run:
```bash
# Formatting & Linting
ruff check . --fix
ruff format .

# Type Checking
mypy agentauth

# Tests
pytest --cov=agentauth
```

Thank you for contributing!
