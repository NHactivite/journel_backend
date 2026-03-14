import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import HTTPException, Cookie, Request
from typing import Optional
import os

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-key")
ALGORITHM  = os.getenv("ALGORITHM", "HS256").strip('"').strip("'")

def get_current_user(request: Request) -> dict:   # ← use Request directly
    token = request.cookies.get("token")           # ← read cookie from request
    
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "userId": payload.get("userId"),
            "email":  payload.get("email"),
        }
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")