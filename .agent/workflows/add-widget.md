---
description: Add a new reusable component to the dashboard widgets
---

# Add a New Dashboard Widget

AgentAuth uses a **BaseWidget** interface for modular and reusable dashboard components. This workflow guides you through creating a new component.

## 1. Create the Widget Class
Create a new file in `agentauth/dashboard/widgets/` (e.g., `my_widget.py`).
- Subclass `BaseWidget` from `agentauth.dashboard.base`.
- Decorate your class with `@widget_registry.register("your_widget_id")`.
- Define `priority` and `group` (e.g., `metric`, `chart`, `table`).
- Implement `def render(self, data: Any) -> html.Div`.

```python
import pandas as pd
from dash import html
from ..base import BaseWidget
from . import widget_registry

@widget_registry.register("requests_per_time")
class RequestsPerTimeWidget(BaseWidget):
    """A chart showing requests per hour."""
    priority = 50
    group = "chart"

    def render(self, data: Any) -> html.Div:
        # Implementation using plotly.express or dash.html
        return html.Div(className="card", children=[...])
```

## 2. Implement Rendering UI
- Use glassmorphic CSS classes: `card`, `metric-card`, `glass-panel`.
- Ensure the widget is responsive and handles `None` or empty `data` gracefully.

## 3. Verify
// turbo-all
source .venv/bin/activate
pytest tests/test_dashboard.py --cov=agentauth.dashboard.widgets --cov-report=term-missing
