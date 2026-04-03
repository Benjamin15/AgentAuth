---
description: Add a new view to the Plotly Dash frontend
---

# Add a New Dashboard Page

AgentAuth uses a **Registry System** for automatic discovery and rendering of dashboard pages. This workflow guides you through creating a new modular page.

## 1. Create the Page Class
Create a new file in `agentauth/dashboard/pages/` (e.g., `my_page.py`).
- Subclass `BasePage` from `agentauth.dashboard.base`.
- Decorate your class with `@page_registry.register("your_page_id")`.
- Define `label`, `icon` (Bootstrap Icons), `section`, and `priority`.

```python
from dash import html
from ..base import BasePage
from . import page_registry

@page_registry.register("my_page")
class MyPage(BasePage):
    label = "My Page"
    icon = "grid-fill"
    section = "analytics"  # core, analytics, models, settings
    priority = 100

    def render(self) -> html.Div:
        return html.Div([
            html.H1("Hello World"),
            # Your components here
        ])
```

## 2. Implement Logic & Widgets
- Use existing components from `agentauth/dashboard/widgets/`.
- If your page requires complex SQL queries or API calls, keep them inside the `render()` method or a helper logic function.

## 3. Verify
// turbo-all
source .venv/bin/activate
pytest tests/test_dashboard.py --cov=agentauth.dashboard --cov-report=term-missing
