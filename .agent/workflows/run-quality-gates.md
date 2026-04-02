---
description: Run formatting, linting, type checking, and unit tests
---

# Run Quality Gates

Use this workflow to make sure your changes haven't broken the build. This runs the same gates as the CI pipeline.

// turbo-all
source .venv/bin/activate
ruff check agentauth --fix
ruff format agentauth
mypy agentauth
pytest --cov=agentauth --cov-report=term-missing
