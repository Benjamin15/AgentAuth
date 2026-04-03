# AgentAuth Extension Guide (AI Skills)

This document serves as the primary "Skill" set for AI coding assistants working on the AgentAuth codebase.

## Unified Architecture: The Registry Pattern
AgentAuth uses a unified `Registry` pattern to enable automatic discovery and modularization. There are three primary extension points:

### 1. Dashboard Pages
- **Path**: `agentauth/dashboard/pages/`
- **Pattern**: Class-based, subclassing `BasePage`.
- **Registry**: `page_registry` (from `.pages`).
- **Use Case**: Adding a new full-screen view with a sidebar link.

### 2. Dashboard Widgets
- **Path**: `agentauth/dashboard/widgets/`
- **Pattern**: Class-based, subclassing `BaseWidget`.
- **Registry**: `widget_registry` (from `.widgets`).
- **Use Case**: Adding a new chart, metric, or table component.

### 3. Integration Adapters
- **Path**: `agentauth/core/adapters/`
- **Pattern**: Class-based, subclassing `BaseAdapter`.
- **Registry**: `adapter_registry` (from `.adapters`).
- **Use Case**: Adding a new upstream LLM or SaaS provider (e.g., OpenAI, Anthropic).

### 4. Alerting Adapters
- **Path**: `agentauth/alerting/adapters/`
- **Pattern**: Class-based, subclassing `BaseAlertAdapter`.
- **Registry**: `alert_registry` (from `.adapters`).
- **Use Case**: Adding a new notification channel (e.g., Slack, Email, Webhook).

---

## Boilerplate Snippets

### Adding a Page
```python
from dash import html
from ..base import BasePage
from . import page_registry

@page_registry.register("my_page_id")
class MyPage(BasePage):
    label = "My Page Label"
    icon = "display"  # Bootstrap icon
    section = "analytics"  # core, analytics, models, settings
    priority = 100

    def render(self) -> html.Div:
        return html.Div([
            html.H1("New Page Content")
        ])
```

### Adding a Widget
```python
from dash import html
from ..base import BaseWidget
from . import widget_registry

@widget_registry.register("my_widget_id")
class MyWidget(BaseWidget):
    priority = 10
    group = "metric" # metric, chart, table

    def render(self, data: Any) -> html.Div:
        return html.Div(className="metric-card", children=[...])
```

### Adding an Adapter
```python
from .base import BaseAdapter
from . import adapter_registry

@adapter_registry.register("my_provider_name")
class MyProviderAdapter(BaseAdapter):
    async def forward(self, request_data: dict[str, Any]) -> dict[str, Any]:
        # Proxy logic here
        return {"status": 200, "response": {...}}
```

### Adding an Alert Adapter
```python
from .base import BaseAlertAdapter, AlertPayload
from . import alert_registry

@alert_registry.register("my_channel_name")
class MyChannelAdapter(BaseAlertAdapter):
    async def send(self, payload: AlertPayload) -> bool:
        # Delivery logic here
        return True
```

## Mandatory Quality Gates
Before concluding any task where you've added or modified any of the above:
1. Run `/run-quality-gates`.
2. Ensure 100% test coverage for the new component.
3. Confirm that `mypy` and `ruff` are clean.
