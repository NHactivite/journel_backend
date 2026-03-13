import bcrypt as bcrypt_lib                        # ← direct bcrypt, no passlib
from fastapi import APIRouter, HTTPException, Response, Cookie
from pydantic import BaseModel
from database import cursor, conn
from jose import jwt
from datetime import datetime, timedelta
import uuid
from typing import Optional
import os

router = APIRouter(prefix="/api/auth", tags=["auth"])

SECRET_KEY  = os.getenv("SECRET_KEY", "fallback-key")
ALGORITHM   = os.getenv("ALGORITHM", "HS256")
EXPIRE_DAYS = int(os.getenv("EXPIRE_DAYS", 7))


# ── DB Table ──────────────────────────────────────────────
cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id         TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        email      TEXT NOT NULL UNIQUE,
        password   TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
""")
conn.commit()

# ── Schemas ───────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# ── Helpers ───────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt_lib.hashpw(
        password.encode("utf-8"),
        bcrypt_lib.gensalt()
    ).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt_lib.checkpw(
        plain.encode("utf-8"),
        hashed.encode("utf-8")
    )

def create_token(user_id: str, email: str) -> str:
    payload = {
        "userId": user_id,
        "email":  email,
        "exp":    datetime.utcnow() + timedelta(days=EXPIRE_DAYS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def set_cookie(response: Response, token: str):
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * EXPIRE_DAYS,
        samesite="lax",
        secure=False,        # set True in production (HTTPS)
    )

# ── Register ──────────────────────────────────────────────
@router.post("/register")
def register(data: RegisterRequest, response: Response):
    existing = cursor.execute(
        "SELECT id FROM users WHERE email = ?", (data.email,)
    ).fetchone()

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user_id         = str(uuid.uuid4())
    hashed_password = hash_password(data.password)

    cursor.execute(
        "INSERT INTO users (id, name, email, password, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, data.name, data.email, hashed_password, datetime.utcnow().isoformat())
    )
    conn.commit()

    token = create_token(user_id, data.email)
    set_cookie(response, token)

    return {
        "message": "Registered successfully",
        "user": { "id": user_id, "name": data.name, "email": data.email }
    }

# ── Login ─────────────────────────────────────────────────
@router.post("/login")
def login(data: LoginRequest, response: Response):
    row = cursor.execute(
        "SELECT id, name, email, password FROM users WHERE email = ?",
        (data.email,)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    user_id, name, email, hashed_password = row

    if not verify_password(data.password, hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token = create_token(user_id, email)
    set_cookie(response, token)

    return {
        "message": f"Welcome back, {name}",
        "user": { "id": user_id, "name": name, "email": email }
    }

# ── Logout ────────────────────────────────────────────────
@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("token")
    return { "message": "Logged out successfully" }

# ── Me (get current user) ─────────────────────────────────
@router.get("/me")
def get_me(token: Optional[str] = Cookie(default=None)):
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("userId")
        row = cursor.execute(
            "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="User not found")
        return { "id": row[0], "name": row[1], "email": row[2] }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")