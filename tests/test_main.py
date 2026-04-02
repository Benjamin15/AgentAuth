from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from agentauth.main import app


def test_app_initialization():
    assert isinstance(app, FastAPI)
    assert app.title == "AgentAuth"


def test_mounts():
    # Check if /dashboard is mounted
    routes = [getattr(r, "path", None) for r in app.routes]
    assert "/dashboard" in routes


@patch("uvicorn.run")
def test_start_function(mock_run):
    from agentauth.main import start

    start()
    mock_run.assert_called_once()


@patch("uvicorn.run")
def test_main_execution(mock_run):
    import sys

    # We must patch sys.argv because uvicorn might look at it
    with patch.object(sys, "argv", ["agentauth"]):
        # Execute the file as __main__
        with open("agentauth/main.py") as f:
            code = compile(f.read(), "agentauth/main.py", "exec")
            globals_dict = {
                "__name__": "__main__",
                "uvicorn": MagicMock(run=mock_run),
                "__package__": "agentauth",
                "__file__": "agentauth/main.py",
            }
            try:
                exec(code, globals_dict)
            except Exception:
                pass
    mock_run.assert_called()
