import uvicorn
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

from .api.router import router as api_router
from .core.database import Base, engine
from .dashboard.app import app as dash_app

# Create DB tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(title="AgentAuth", description="IAM for LLM Agents")

# Include Proxy API routes
app.include_router(api_router)

# Mount Dash WSGI App at /dashboard
app.mount("/dashboard", WSGIMiddleware(dash_app.server))


def start():
    # When running as a package, use the module path
    uvicorn.run("agentauth.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
