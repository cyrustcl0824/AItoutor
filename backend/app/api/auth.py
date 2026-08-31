from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Family, User
from ..schemas import LoginRequest, RegisterRequest, UserOut
from ..security import decode_token, hash_password, set_auth_cookies, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="Email already registered")
    family = Family(name=payload.family_name)
    db.add(family)
    db.flush()
    user = User(family_id=family.id, email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    set_auth_cookies(response, user)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    set_auth_cookies(response, user)
    return user


@router.post("/refresh", response_model=UserOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    payload = decode_token(request.cookies.get("refresh_token", ""), "refresh")
    user = db.get(User, payload["sub"])
    if not user or payload.get("version") != user.refresh_version:
        raise HTTPException(status_code=401, detail="Refresh session revoked")
    user.refresh_version += 1
    db.commit()
    set_auth_cookies(response, user)
    return user


@router.post("/logout", status_code=204)
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.refresh_version += 1
    db.commit()
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

