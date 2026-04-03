---
description: Add a new alerting adapter (Slack, SNS, Email) to AgentAuth
---

# Add a New Alerting Adapter

AgentAuth uses a **BaseAlertAdapter** strategy for delivering notifications when budget thresholds are crossed. This workflow guides you through implementing a new delivery channel.

## 1. Create the Adapter Class
Create a new file in `agentauth/alerting/adapters/` (e.g., `sns_adapter.py`).
- Subclass `BaseAlertAdapter` from `agentauth.alerting.base`.
- Decorate your class with `@alert_registry.register("your_channel_id")`.
- Implement `async def send(self, payload: AlertPayload) -> bool`.

```python
from .base import BaseAlertAdapter, AlertPayload
from . import alert_registry

@alert_registry.register("email")
class EmailAlertAdapter(BaseAlertAdapter):
    """Adapter for Email notifications."""

    async def send(self, payload: AlertPayload) -> bool:
        try:
            # Send logic here (e.g. SMTP or SendGrid)
            # Use payload.subject and payload.body for content
            return True
        except Exception:
            # Suppression is mandatory: delivery failure should not crash proxy
            return False
```

## 2. Integration & Verification
The alerting engine automatically discovers new adapters. You can test your new adapter using the `/alerts` dashboard page or by inducing a simulated budget breach in development.

## 3. Verify
// turbo-all
source .venv/bin/activate
pytest tests/test_alerting.py --cov=agentauth.alerting.adapters --cov-report=term-missing
