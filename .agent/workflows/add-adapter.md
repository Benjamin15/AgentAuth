---
description: Add a new integration adapter to AgentAuth
---

# Add a New Integration Adapter

Adapters bridge the gap between AgentAuth and external LLM/SaaS providers (OpenAI, Anthropic, Gemini). This workflow guides you through creating a new modular adapter.

## 1. Create the Adapter Class
Create a new file in `agentauth/core/adapters/` (e.g., `openai_adapter.py`).
- Subclass `BaseAdapter` from `agentauth.core.adapters.base`.
- Decorate your class with `@adapter_registry.register("your_provider_id")`.
- Implement `async def forward(self, request_data: dict[str, Any]) -> dict[str, Any]`.

```python
from typing import Any
from .base import BaseAdapter
from . import adapter_registry

@adapter_registry.register("openai")
class OpenAIAdapter(BaseAdapter):
    """Adapter for OpenAI API."""

    async def forward(self, request_data: dict[str, Any]) -> dict[str, Any]:
        # Implementation here
        # Return a dict with model, tokens, and cost mapping.
```

## 2. Implement Forwarding Logic
- Use standard HTTP libraries (`httpx` or `requests`).
- Map provider-specific usage metrics (prompt/completion tokens) to a unified format.
- Gracefully handle API errors and return non-200 statuses where appropriate.

## 3. Verify
// turbo-all
source .venv/bin/activate
pytest tests/test_api.py --cov=agentauth.core.adapters --cov-report=term-missing
