# AgentAuth: IAM for AI Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)

**AgentAuth** is an open-source Identity and Access Management (IAM) platform specifically designed for AI agents and LLM-based applications. It provides a secure proxy layer to manage non-human identities, enforce granular permissions, and monitor activity with a beautiful analytics dashboard.

## 🚀 Key Features

- **Agent Management**: Create, name, and manage unique identities for your AI agents.
- **Scoped Permissions**: Grant or revoke access to specific integrations (Gemini, OpenAI, etc.) per agent.
- **Security Proxy**: A secure `/v1/proxy/{integration}` endpoint that handles API keys and enforces IAM policies.
- **Kill Switch**: Instantly freeze any agent to block all its upstream API access.
- **Analytics Dashboard**: Real-time visualization of request trends, success rates, and integration usage.
- **Audit Logs**: Comprehensive logs of every interaction for security and debugging.

## 🛠️ Architecture

AgentAuth is built with a modern Python stack:
- **FastAPI**: High-performance backend API and proxy.
- **Plotly Dash**: Interactive glassmorphism dashboard.
- **SQLAlchemy + SQLite**: Robust data persistence.
- **Pydantic Settings**: Secure and flexible configuration management.

## 📦 Project Structure

```
.
├── agentauth/                 # Main Python package
│   ├── core/                  # Database models, security, and configuration
│   ├── api/                   # FastAPI routes and core logic
│   └── dashboard/             # Dash UI, layouts, and assets
├── scripts/                   # Utility scripts for data generation
├── tests/                     # Comprehensive test suite
├── README.md                  # This file
└── pyproject.toml             # Project metadata and dependencies
```

## 🚦 Getting Started

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Benjamin15/AgentAuth
cd AgentAuth

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package in editable mode
pip install -e .
```

### 2. Configuration

Create a `.env` file in the root directory:
```env
AGENTAUTH_JWT_SECRET=your-secret-key-here
DATABASE_URL=sqlite:///./agentauth.db
```

### 3. Running the Server

Start the FastAPI server with the Dashboard using the built-in CLI:
```bash
agentauth
```
Then visit `http://127.0.0.1:8000/dashboard/`.

### 4. Usage Example

To proxy a request through AgentAuth for an agent:
```bash
curl -X POST "http://127.0.0.1:8000/v1/proxy/gemini" \
     -H "Authorization: Bearer <AGENT_API_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"contents": [{"parts": [{"text": "Hello world!"}]}]}'
```

## 👨‍💻 Developer Guidelines

If you are contributing to this project, please read the [CONTRIBUTING.md](./CONTRIBUTING.md) and [AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md) files.

The project enforces strict quality gates:
- **100% Code Coverage** is required (`pytest --cov=agentauth`)
- **Static Typing** is enforced via MyPy (`mypy agentauth`)
- **Linting & Formatting** is managed by Ruff (`ruff check` & `ruff format`)
- **Pre-commit Hooks** run locally to prevent bad commits (`pre-commit install`)

## 📄 License

This project is open-source and available under the **MIT License**. See the [LICENSE](./LICENSE) file for more details.
