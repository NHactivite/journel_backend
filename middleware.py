import jwt                                        # ← PyJWT
from jwt.exceptions import InvalidTokenError      # ← PyJWT exception
from fastapi import HTTPException, Cookie
from typing import Optional
import os

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-key")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")

def get_current_user(token: Optional[str] = Cookie(default=None)) -> dict:
    """
    Use this as a dependency in any protected route.

    Example:
        @app.get("/api/journal/{user_id}")
        def get_journals(user_id: str, user=Depends(get_current_user)):
            ...
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "userId": payload.get("userId"),
            "email":  payload.get("email"),
        }
    except InvalidTokenError:                     # ← was: except Exception
        raise HTTPException(status_code=401, detail="Invalid or expired token")