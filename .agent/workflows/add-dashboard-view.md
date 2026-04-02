---
description: Add a new view to the Plotly Dash frontend
---

# Add a New Dashboard View

This workflow guarantees the Dash layout stays "Glassmorphic" and the code stays 100% testable.

## 1. Create UI Components
Open `agentauth/dashboard/app.py`.
- Define your new view in a function like `def get_my_new_view():`.
- Use existing components wrapper like `html.Div(className="glass-panel", ...)`.
- Add any required buttons or inputs. Avoid adding states/callbacks directly in the layout.

## 2. Separate Logic from Callbacks
If your UI has interactions (clicks, submits):
- Avoid writing raw business logic inside the `@app.callback(render_page)` function.
- Create a corresponding pure Python logic function in the "Logic Functions" section, e.g., `def handle_my_interaction_logic(...)`.
- Call this pure function inside the Dash callback.

## 3. Write Tests
Open `tests/test_dashboard.py`.
- Test your pure Python logic function explicitly (e.g., test input values -> return values).
- You are strictly forbidden from writing tests that launch the Dash application or rely on a browser driver unless absolutely necessary.
- Achieving 100% test coverage for the logic function is mandatory.

## 4. Validate
// turbo-all
source .venv/bin/activate
pytest tests/test_dashboard.py --cov=agentauth.dashboard --cov-report=term-missing
