from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import get_settings
from .models import User

ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except Exception:
        return False


def create_token(user: User, token_type: str) -> str:
    settings = get_settings()
    lifetime = timedelta(minutes=settings.access_token_minutes) if token_type == "access" else timedelta(days=settings.refresh_token_days)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "family_id": user.family_id,
        "role": user.role,
        "type": token_type,
        "version": user.refresh_version,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            raise ValueError("wrong token type")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session") from exc


def current_user(request: Request, db: Session) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_token(token, "access")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


def set_auth_cookies(response, user: User) -> None:
    secure = get_settings().cookie_secure
    response.set_cookie("access_token", create_token(user, "access"), httponly=True, secure=secure, samesite="lax", max_age=900)
    response.set_cookie("refresh_token", create_token(user, "refresh"), httponly=True, secure=secure, samesite="lax", max_age=30 * 86400)

