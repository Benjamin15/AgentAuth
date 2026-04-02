---
description: Add a new upstream AI integration provider to AgentAuth
---

# Add a New Integration Provider

This workflow helps you add a new upstream integration (like Anthropic, OpenAI) to the AgentAuth system.

## 1. Create the Adapter
Open `agentauth/core/adapters.py` and create a new class inheriting from `BaseAdapter`.
Ensure you implement the `forward(self, request_data: Dict[str, Any]) -> Dict[str, Any]` method.
Remember to type-hint everything (MyPy rule) and use `cast(Dict[str, Any], ...)` if loading raw JSON.

## 2. Update the Router
Open `agentauth/api/router.py`. In the `/v1/proxy/{integration_name}` route:
- Import your new Adapter.
- Add an `elif integration_name == "your_provider":` block.
- Instantiate the adapter with the necessary `provider_key`.

## 3. Write Unit Tests
Open `tests/test_api.py`.
- Write a test `test_proxy_success_your_provider(client, db_session)`.
- Use `@patch('agentauth.core.adapters.YourProviderAdapter.forward')` to mock the external API call.
- Assert that the response matches expectations and the status is 200.

## 4. Run Quality Gates
Run the `run-quality-gates` workflow or execute:

// turbo-all
source .venv/bin/activate
ruff check agentauth --fix
ruff format agentauth
mypy agentauth
pytest --cov=agentauth --cov-report=term-missing

Ensure code coverage remains at 100%.
