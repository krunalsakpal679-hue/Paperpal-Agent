# backend/app/middleware/auth.py
"""
JWT authentication middleware.

Validates Bearer tokens on protected routes. Skips authentication
for public endpoints like /health, /docs, and /openapi.json.
"""

import logging

from fastapi import Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# Routes that do not require authentication
PUBLIC_PATHS: set[str] = {
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class JWTMiddleware(BaseHTTPMiddleware):
    """Middleware that validates JWT tokens on protected routes."""

    async def dispatch(self, request: Request, call_next):
        """
        Check Authorization header for valid JWT token.

        In development mode, authentication is optional (permissive).
        """
        path = request.url.path

        # Skip auth for public paths and OPTIONS (CORS preflight)
        if path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # In development, allow unauthenticated requests
        if settings.is_development:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                request.state.user_id = None
                return await call_next(request)

        # Extract and validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )
            request.state.user_id = payload.get("sub")
        except JWTError as exc:
            logger.warning("JWT validation failed: %s", exc)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        return await call_next(request)
