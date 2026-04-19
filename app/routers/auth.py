from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.dependencies.auth import get_validated_token_payload
from app.models import RefreshToken, RevokedToken, User, UserType
from app.schemas import (
    LogoutRequest,
    RefreshTokenRequest,
    Token,
    UserLogin,
    UserOut,
    UserRegister,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def _issue_token_pair(user_id: int, db: AsyncSession) -> Token:
    access_token, access_expires_at, _ = create_access_token(data={"sub": str(user_id)})
    refresh_token, refresh_expires_at, refresh_jti = create_refresh_token(data={"sub": str(user_id)})

    db.add(
        RefreshToken(
            jti=refresh_jti,
            user_id=user_id,
            expires_at=refresh_expires_at,
        )
    )
    await db.flush()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def _revoke_access_token(payload: dict, db: AsyncSession) -> None:
    result = await db.execute(select(RevokedToken).where(RevokedToken.jti == payload["jti"]))
    if result.scalar_one_or_none():
        return

    db.add(
        RevokedToken(
            jti=payload["jti"],
            user_id=int(payload["sub"]),
            token_type="access",
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    )
    await db.flush()


async def _revoke_refresh_token(refresh_token: str, user_id: int, db: AsyncSession) -> None:
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    refresh_jti = payload.get("jti")
    refresh_user_id = payload.get("sub")
    if refresh_jti is None or refresh_user_id is None or int(refresh_user_id) != user_id:
        raise HTTPException(status_code=401, detail="Refresh token does not belong to current user")

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == refresh_jti))
    token_row = result.scalar_one_or_none()
    if token_row is None:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    if token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(timezone.utc)
        await db.flush()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    result = await db.execute(select(UserType).where(UserType.id == 2))
    customer_type = result.scalar_one_or_none()
    if not customer_type:
        customer_type = UserType(id=2, name="customer")
        db.add(customer_type)
        await db.flush()

    user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),
        phone=data.phone,
        birth_date=data.birth_date,
        user_type_id=2,
        is_confirm=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.utcnow()
    await db.flush()

    return await _issue_token_pair(user_id=user.id, db=db)


@router.post("/refresh", response_model=Token)
async def refresh_tokens(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    refresh_jti = payload.get("jti")
    user_id = payload.get("sub")
    if refresh_jti is None or user_id is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == refresh_jti))
    token_row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if (
        token_row is None
        or token_row.user_id != int(user_id)
        or token_row.revoked_at is not None
        or token_row.expires_at <= now
    ):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    token_row.revoked_at = now
    await db.flush()

    return await _issue_token_pair(user_id=int(user_id), db=db)


@router.post("/logout")
async def logout(
    data: LogoutRequest | None = Body(default=None),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    payload = await get_validated_token_payload(token=token, db=db, expected_type="access")
    await _revoke_access_token(payload=payload, db=db)

    if data and data.refresh_token:
        await _revoke_refresh_token(
            refresh_token=data.refresh_token,
            user_id=int(payload["sub"]),
            db=db,
        )

    return {"message": "Logged out successfully"}
