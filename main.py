from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from database import engine, Base
from api import router as api_router
from dash_app import app as dash_app

# Create DB tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(title="AgentAuth", description="IAM for LLM Agents")

# Include Proxy API routes
app.include_router(api_router)

# Mount Dash WSGI App at /dashboard
app.mount("/dashboard", WSGIMiddleware(dash_app.server))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
