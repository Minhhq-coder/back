from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models import Notification, User
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/me", response_model=list[NotificationOut])
async def list_my_notifications(
    current_user: User = Depends(require_permission("notifications:read")),
    db: AsyncSession = Depends(get_db),
):
    filters = [Notification.user_id == current_user.id]
    if current_user.user_type_id == 1:
        filters.append(Notification.target_role == "admin")

    result = await db.execute(
        select(Notification)
        .where(or_(*filters))
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.put("/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(require_permission("notifications:read")),
    db: AsyncSession = Depends(get_db),
):
    filters = [Notification.user_id == current_user.id]
    if current_user.user_type_id == 1:
        filters.append(Notification.target_role == "admin")

    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            or_(*filters),
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.is_read = True
    await db.flush()
    await db.refresh(notification)
    return notification
