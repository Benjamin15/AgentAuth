# AgentAuth: IAM for AI Agents

AgentAuth is an open-source Identity and Access Management (IAM) platform specifically designed for AI agents and LLM-based applications. It provides a secure proxy layer to manage non-human identities, enforce granular permissions, and monitor activity with a beautiful analytics dashboard.

## 🚀 Key Features

- **Agent Management**: Create, name, and manage unique identities for your AI agents.
- **Scoped Permissions**: Grant or revoke access to specific integrations (Gemini, OpenAI, etc.) per agent.
- **Security Proxy**: A secure `/v1/proxy/{integration}` endpoint that handles API keys and enforces IAM policies.
- **Kill Switch**: Instantly freeze any agent to block all its upstream API access.
- **Analytics Dashboard**: Real-time visualization of request trends, success rates, and integration usage using Plotly.
- **Audit Logs**: Comprehensive logs of every interaction for security and debugging.

## 🛠️ Architecture

AgentAuth is built with a modern Python stack:
- **FastAPI**: High-performance backend API and proxy.
- **Plotly Dash**: Interactive glassmorphism dashboard.
- **SQLAlchemy + SQLite**: Robust data persistence.
- **Adapters Pattern**: Extensible support for any third-party AI provider.

## 📦 Project Structure

```
.
├── agentauth/                 # Main Python package
│   ├── core/                  # Database models and adapters
│   ├── api/                   # FastAPI routes
│   └── dashboard/             # Dash UI and assets
├── scripts/                   # Utility scripts (Mock data etc.)
├── README.md                  # This file
└── requirements.txt           # Project dependencies
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

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Server
```bash
# Start the FastAPI server with the Dashboard
uvicorn agentauth.main:app --reload --port 8000
```
Then visit `http://127.0.0.1:8000/dashboard/`.

### 3. Usage Example
To proxy a request through AgentAuth for an agent:
```bash
curl -X POST "http://127.0.0.1:8000/v1/proxy/gemini" \
     -H "Authorization: Bearer <AGENT_API_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"contents": [{"parts": [{"text": "Hello world!"}]}]}'
```

## 📄 License
This project is open-source and available under the MIT License.
