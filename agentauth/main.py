import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from .api.router import router as api_router
from .core.database import Base, engine
from .core.security import decode_access_token
from .dashboard.app import app as dash_app
from .dashboard.auth_ui import router as auth_router

# Create DB tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(title="AgentAuth", description="IAM for LLM Agents")

# Include Proxy API routes
app.include_router(api_router)

# Include Auth UI routes
app.include_router(auth_router)


class DashboardAuthMiddleware(BaseHTTPMiddleware):  # type: ignore
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/dashboard"):
            token = request.cookies.get("access_token")
            if not token or not token.startswith("Bearer "):
                return RedirectResponse("/login", status_code=303)
            try:
                jwt_token = token.split(" ")[1]
                decode_access_token(jwt_token)
            except Exception:
                return RedirectResponse("/login", status_code=303)
        return await call_next(request)


app.add_middleware(DashboardAuthMiddleware)

# Mount Dash WSGI App at /dashboard
app.mount("/dashboard", WSGIMiddleware(dash_app.server))


def start():
    # When running as a package, use the module path
    uvicorn.run("agentauth.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
