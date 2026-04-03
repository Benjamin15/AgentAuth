from collections.abc import Awaitable
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response

from .security import decode_access_token


class DashboardAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to protect /dashboard routes by checking for a valid JWT in cookies."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
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
