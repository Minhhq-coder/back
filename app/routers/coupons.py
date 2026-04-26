from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models import Coupon, User
from app.schemas import (
    CouponCreate,
    CouponOut,
    CouponUpdate,
    CouponValidateIn,
    CouponValidateOut,
)
from app.services.coupon_service import (
    get_coupon_by_code,
    normalize_coupon_code,
    validate_coupon_for_subtotal,
)

router = APIRouter(tags=["Coupons"])


async def _get_coupon_or_404(db: AsyncSession, coupon_id: int) -> Coupon:
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return coupon


async def _ensure_unique_code(db: AsyncSession, code: str, coupon_id: int | None = None) -> str:
    normalized_code = normalize_coupon_code(code)
    query = select(Coupon).where(func.upper(Coupon.code) == normalized_code)
    if coupon_id is not None:
        query = query.where(Coupon.id != coupon_id)

    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Coupon code already exists")

    return normalized_code


@router.post("/coupons/validate", response_model=CouponValidateOut)
async def validate_coupon(
    payload: CouponValidateIn,
    db: AsyncSession = Depends(get_db),
):
    coupon = await get_coupon_by_code(db, payload.code)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    discount = validate_coupon_for_subtotal(coupon, payload.subtotal)
    return CouponValidateOut(
        code=coupon.code,
        discount_amount=discount,
        subtotal=payload.subtotal,
        total=max(payload.subtotal - discount, 0),
        message="Coupon applied successfully.",
    )


@router.get("/admin/coupons", response_model=list[CouponOut])
async def list_coupons(
    _: User = Depends(require_permission("orders:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Coupon).order_by(Coupon.created_at.desc()))
    return result.scalars().all()


@router.post("/admin/coupons", response_model=CouponOut, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    payload: CouponCreate,
    _: User = Depends(require_permission("orders:manage")),
    db: AsyncSession = Depends(get_db),
):
    code = await _ensure_unique_code(db, payload.code)
    coupon = Coupon(**payload.model_dump(exclude={"code"}), code=code)
    db.add(coupon)
    await db.flush()
    await db.refresh(coupon)
    return coupon


@router.put("/admin/coupons/{coupon_id}", response_model=CouponOut)
async def update_coupon(
    coupon_id: int,
    payload: CouponUpdate,
    _: User = Depends(require_permission("orders:manage")),
    db: AsyncSession = Depends(get_db),
):
    coupon = await _get_coupon_or_404(db, coupon_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "code" in update_data:
        update_data["code"] = await _ensure_unique_code(db, update_data["code"], coupon.id)

    for field, value in update_data.items():
        setattr(coupon, field, value)

    await db.flush()
    await db.refresh(coupon)
    return coupon


@router.delete("/admin/coupons/{coupon_id}", response_model=dict)
async def delete_coupon(
    coupon_id: int,
    _: User = Depends(require_permission("orders:manage")),
    db: AsyncSession = Depends(get_db),
):
    coupon = await _get_coupon_or_404(db, coupon_id)
    await db.delete(coupon)
    await db.flush()
    return {"deleted": True, "coupon_id": coupon_id}
