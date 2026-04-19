from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.models import RevokedToken, User, UserType

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_optional_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_validated_token_payload(
    token: str,
    db: AsyncSession,
    expected_type: str = "access",
) -> dict:
    payload = decode_token(token)
    if payload is None:
        raise _credentials_exception()

    token_type = payload.get("type")
    user_id = payload.get("sub")
    jti = payload.get("jti")
    if token_type != expected_type or user_id is None or jti is None:
        raise _credentials_exception()

    result = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
    revoked_token = result.scalar_one_or_none()
    if revoked_token and revoked_token.expires_at > datetime.now(timezone.utc):
        raise _credentials_exception()

    return payload


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = await get_validated_token_payload(token=token, db=db, expected_type="access")
    user_id = int(payload["sub"])

    result = await db.execute(
        select(User)
        .options(selectinload(User.user_type).selectinload(UserType.permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise _credentials_exception()
    return user


async def get_optional_current_user(
    token: str | None = Depends(oauth2_optional_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not token:
        return None

    try:
        payload = await get_validated_token_payload(token=token, db=db, expected_type="access")
    except HTTPException:
        return None

    user_id = int(payload["sub"])
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_type).selectinload(UserType.permissions))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


def require_permission(permission_code: str):
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        permissions = {
            permission.code
            for permission in getattr(current_user.user_type, "permissions", [])
        }
        if permission_code not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_code}' required",
            )
        return current_user

    return dependency


async def require_admin(current_user: User = Depends(require_permission("admin:access"))) -> User:
    return current_user
