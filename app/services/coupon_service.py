from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Coupon


def normalize_coupon_code(code: str | None) -> str:
    return (code or "").strip().upper()


def calculate_coupon_discount(coupon: Coupon, subtotal: float) -> float:
    if coupon.discount_type == "percent":
        discount = subtotal * coupon.discount_value / 100
    else:
        discount = coupon.discount_value

    if coupon.max_discount is not None:
        discount = min(discount, coupon.max_discount)

    return round(min(max(discount, 0), subtotal), 2)


async def get_coupon_by_code(db: AsyncSession, code: str) -> Coupon | None:
    normalized_code = normalize_coupon_code(code)
    if not normalized_code:
        return None

    result = await db.execute(
        select(Coupon).where(func.upper(Coupon.code) == normalized_code)
    )
    return result.scalar_one_or_none()


def validate_coupon_for_subtotal(coupon: Coupon, subtotal: float) -> float:
    now = datetime.utcnow()

    if not coupon.is_active:
        raise HTTPException(status_code=400, detail="Coupon is not active")
    if coupon.start_at and coupon.start_at > now:
        raise HTTPException(status_code=400, detail="Coupon is not available yet")
    if coupon.end_at and coupon.end_at < now:
        raise HTTPException(status_code=400, detail="Coupon has expired")
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached")
    if subtotal < coupon.min_order_value:
        raise HTTPException(
            status_code=400,
            detail=f"Order subtotal must be at least {coupon.min_order_value:,.0f} VND",
        )

    return calculate_coupon_discount(coupon, subtotal)
