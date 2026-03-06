# backend/app/middleware/auth.py
from fastapi import Request, HTTPException
from jose import JWTError, jwt
from app.config import settings

class JWTBearer:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(self, request: Request) -> str:
        # Skip auth for public paths
        skip_paths = {"/health", "/api/v1/health", "/api/v1/styles", "/docs", "/openapi.json"}
        if request.url.path in skip_paths:
            return "guest"

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            if self.auto_error:
                raise HTTPException(status_code=401, detail="Missing authorization header")
            return None
        
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid token format")

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid user_id in token")
            return user_id
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
