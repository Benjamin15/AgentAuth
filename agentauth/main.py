import uvicorn
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

from .api.router import router as api_router
from .core.config import settings
from .core.middleware import DashboardAuthMiddleware
from .dashboard.app import app as dash_app
from .dashboard.auth_ui import router as auth_router

# Initialize FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="IAM for LLM Agents",
    version="0.1.0",
)

# Add Security Middleware
app.add_middleware(DashboardAuthMiddleware)

# Include Proxy API routes
app.include_router(api_router)

# Include Auth UI routes
app.include_router(auth_router)

# Mount Dash WSGI App at /dashboard
app.mount("/dashboard", WSGIMiddleware(dash_app.server))


def start() -> None:
    """Entry point for starting the FastAPI application with Uvicorn."""
    uvicorn.run(
        "agentauth.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
    )


if __name__ == "__main__":
    start()
