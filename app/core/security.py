from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from app.core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Invalid hash format (e.g. plain-text password stored in DB)
        return False


def _create_token(
    data: dict,
    token_type: str,
    expires_delta: timedelta,
) -> tuple[str, datetime, str]:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    jti = uuid4().hex
    to_encode.update({"exp": expire, "type": token_type, "jti": jti})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM), expire, jti


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime, str]:
    return _create_token(
        data=data,
        token_type="access",
        expires_delta=expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime, str]:
    return _create_token(
        data=data,
        token_type="refresh",
        expires_delta=expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
