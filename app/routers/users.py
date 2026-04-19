from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import UPLOAD_DIR
from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models import User
from app.schemas import AvatarUploadResponse, UserProfileOut, UserUpdate

router = APIRouter(tags=["Users"])

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
AVATAR_DIR = PROJECT_ROOT / UPLOAD_DIR / "avatars"


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


@router.put("/me", response_model=UserProfileOut)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(require_permission("profile:update")),
    db: AsyncSession = Depends(get_db),
):
    if data.email and data.email != current_user.email:
        result = await db.execute(select(User).where(User.email == data.email, User.id != current_user.id))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = data.email

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
