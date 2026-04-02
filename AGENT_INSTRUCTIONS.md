# Agent Instructions: Coding Guidelines for AgentAuth

Welcome to the AgentAuth codebase! If you are an AI agent or a developer continuing work on this project, you **MUST** adhere to the following rules and understand the architectural principles to ensure the project remains high-quality, typed, and fully tested.

## 1. Project Architecture

AgentAuth is a modular IAM (Identity and Access Management) and observability platform tailored for AI agents. It follows a clean architecture separating the API/Proxy routing, UI dashboard, and core database interactions.

**Directory Structure:**
- `agentauth/api/router.py`: FastAPI endpoints for proxying requests, managing agents, and asserting permissions.
- `agentauth/dashboard/app.py`: Plotly Dash frontend using a modern "Glassmorphism" design. **Note:** UI components and business logic are separated. Business logic is extracted into pure Python functions (e.g., `render_page_logic`) to make them testable without Dash context.
- `agentauth/core/`:
  - `models.py`: SQLAlchemy ORM models (`Agent`, `Integration`, `AuditLog`, `AgentPermission`).
  - `database.py`: DB connection handling (SQLite by default).
  - `adapters.py`: Upstream AI provider integrations (e.g., Gemini, Mock).
- `tests/`: Pytest suite with fixtures mimicking database state and client requests.

## 2. Unbreakable Rules

### Rule #1: 100% Code Coverage is Non-Negotiable
- The project currently maintains **100% test coverage**.
- If you add a new feature, a new API route, or a new dashboard view, you **must** write corresponding unit tests in the `tests/` directory.
- The CI pipeline (`.github/workflows/ci.yml`) is configured to fail if code coverage drops below 100%. Check coverage locally with:
  ```bash
  pytest --cov=agentauth --cov-report=term-missing
  ```

### Rule #2: Static Typing with MyPy
- The project enforces static typing across the `agentauth` package.
- Use explicit type hints for function signatures, especially arguments and return types.
- Be careful with SQLAlchemy column types when passing them to the UI; Dash expects raw types like `str` or `int`, not `Column[str]`. Use explicit casting (e.g., `str(agent.description)`) when necessary.
- Check typing locally with:
  ```bash
  mypy agentauth
  ```

### Rule #3: Linting and Formatting with Ruff
- We use `ruff` exclusively for linting, formatting, and analyzing the code.
- Pre-commit hooks are installed and will reject commits with formatting issues or unused variables.
- Run Ruff checks locally before committing:
  ```bash
  ruff check agentauth --fix
  ruff format agentauth
  ```

### Rule #4: Docstrings and Readability
- Use clear docstrings for new modules, classes, and complex functions.
- Keep the codebase readable. Refactor complex branches into smaller, testable functions instead of nesting logic deeply.

## 3. Pre-Commit Hooks
Before committing any code, ensure you have initialized the pre-commit environment:
```bash
pre-commit install
```
This runs MyPy, Ruff, and various whitespace/syntax checkers on every commit.

## 4. UI/UX Design System
- If you modify the `agentauth/dashboard/app.py`, maintain the **Glassmorphism** styling.
- Use existing CSS classes (`.glass-panel`, `.btn-premium`, `.grid-layout`) to keep the interface premium, clean, and consistent.

## 5. Mocking and Third-Party Dependencies
- For external integrations (like Gemini), wrap them in the `BaseAdapter` pattern defined in `agentauth/core/adapters.py`.
- In tests, use `unittest.mock.patch` to mock external API calls to avoid hitting live endpoints.
