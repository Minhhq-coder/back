from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import UPLOAD_DIR
from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models import Cart, Order, User
from app.schemas import AvatarUploadResponse, MembershipSummaryOut, UserProfileOut, UserUpdate
from app.services.membership_service import get_user_membership_summary

router = APIRouter(tags=["Users"])

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
AVATAR_DIR = PROJECT_ROOT / UPLOAD_DIR / "avatars"


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _build_profile_response(user: User) -> UserProfileOut:
    permissions = sorted(
        getattr(user.user_type, "permissions", []),
        key=lambda permission: permission.code,
    )
    return UserProfileOut(
        id=user.id,
        name=user.name,
        email=user.email,
        address=user.address,
        phone=user.phone,
        avatar=user.avatar,
        birth_date=user.birth_date,
        is_confirm=user.is_confirm,
        user_type_id=user.user_type_id,
        role=user.user_type.name,
        permissions=permissions,
    )


@router.get("/me", response_model=UserProfileOut)
async def get_my_profile(
    current_user: User = Depends(require_permission("profile:read")),
):
    return _build_profile_response(current_user)


@router.get("/me/membership", response_model=MembershipSummaryOut)
async def get_my_membership(
    current_user: User = Depends(require_permission("profile:read")),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_membership_summary(db, current_user.id)


@router.put("/me", response_model=UserProfileOut)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(require_permission("profile:update")),
    db: AsyncSession = Depends(get_db),
):
    normalized_email = _normalize_email(data.email) if data.email else None

    if normalized_email and normalized_email != _normalize_email(current_user.email):
        result = await db.execute(
            select(User).where(
                func.lower(User.email) == normalized_email,
                User.id != current_user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = normalized_email

    update_data = data.model_dump(exclude_unset=True, exclude={"email"})
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.flush()
    await db.refresh(current_user)
    return _build_profile_response(current_user)


@router.post("/me/avatar", response_model=AvatarUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("profile:upload_avatar")),
    db: AsyncSession = Depends(get_db),
):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Avatar file is too large")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{current_user.id}-{uuid4().hex}{extension}"
    destination = AVATAR_DIR / filename
    destination.write_bytes(content)

    current_user.avatar = f"/{UPLOAD_DIR}/avatars/{filename}".replace("\\", "/")
    await db.flush()

    return AvatarUploadResponse(avatar=current_user.avatar)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    current_user: User = Depends(require_permission("profile:delete")),
    db: AsyncSession = Depends(get_db),
):
    avatar_path = None
    if current_user.avatar and current_user.avatar.startswith(f"/{UPLOAD_DIR}/"):
        avatar_path = PROJECT_ROOT / current_user.avatar.lstrip("/")

    cart_result = await db.execute(select(Cart).where(Cart.user_id == current_user.id))
    cart = cart_result.scalar_one_or_none()
    if cart:
        await db.delete(cart)

    orders_result = await db.execute(select(Order).where(Order.user_id == current_user.id))
    for order in orders_result.scalars().all():
        order.user_id = None

    await db.flush()
    await db.delete(current_user)
    await db.flush()

    if avatar_path and avatar_path.exists():
        try:
            avatar_path.unlink()
        except OSError:
            pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)
