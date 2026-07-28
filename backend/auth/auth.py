from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
import hashlib
import bcrypt

from backend.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from backend.core.logger import logger
from backend.database.db import get_user_by_email, create_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    email: str
    password: str


# -------- PASSWORD HASHING (direct bcrypt — passlib bypass) --------

def hash_password(p: str) -> str:
    """
    Supports unlimited password length safely.
    Step 1: SHA256 normalize (ensures < 72 bytes)
    Step 2: bcrypt hash directly
    """
    sha = hashlib.sha256(p.encode("utf-8")).hexdigest()[:72]
    return bcrypt.hashpw(sha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    sha = hashlib.sha256(plain.encode("utf-8")).hexdigest()[:72]
    try:
        return bcrypt.checkpw(sha.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# ---------------------------------------------------------


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            raise exc

    except JWTError:
        raise exc

    user = await get_user_by_email(email)

    if not user:
        raise exc

    if not user.get("is_active"):
        raise HTTPException(
            status_code=403,
            detail="User account disabled."
        )

    return user


async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    return current_user


async def authenticate_user(email, password):
    user = await get_user_by_email(email)

    if not user or not verify_password(password, user["hashed_password"]):
        return None

    return user


async def register_user(email, password):
    if await get_user_by_email(email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered."
        )

    await create_user(email, hash_password(password))

    logger.info(f"User registered: {email}")

    return {
        "email": email,
        "is_active": True,
        "is_verified": False
    }