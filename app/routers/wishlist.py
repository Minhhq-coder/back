from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models import Product, User, WishlistItem
from app.schemas import WishlistItemOut

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


async def _get_public_product_or_404(db: AsyncSession, product_id: int) -> Product:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_active == True,  # noqa: E712
            Product.is_deleted == False,  # noqa: E712
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("", response_model=list[WishlistItemOut])
async def list_wishlist(
    current_user: User = Depends(require_permission("profile:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WishlistItem)
        .options(selectinload(WishlistItem.product))
        .join(Product, Product.id == WishlistItem.product_id)
        .where(
            WishlistItem.user_id == current_user.id,
            Product.is_active == True,  # noqa: E712
            Product.is_deleted == False,  # noqa: E712
        )
        .order_by(WishlistItem.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{product_id}", response_model=WishlistItemOut, status_code=status.HTTP_201_CREATED)
async def add_to_wishlist(
    product_id: int,
    current_user: User = Depends(require_permission("profile:read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_public_product_or_404(db, product_id)

    result = await db.execute(
        select(WishlistItem)
        .options(selectinload(WishlistItem.product))
        .where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == product_id,
        )
    )
    item = result.scalar_one_or_none()
    if item:
        return item

    item = WishlistItem(user_id=current_user.id, product_id=product_id)
    db.add(item)
    await db.flush()

    result = await db.execute(
        select(WishlistItem)
        .options(selectinload(WishlistItem.product))
        .where(WishlistItem.id == item.id)
    )
    return result.scalar_one()


@router.delete("/{product_id}", response_model=dict)
async def remove_from_wishlist(
    product_id: int,
    current_user: User = Depends(require_permission("profile:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == product_id,
        )
    )
    item = result.scalar_one_or_none()
    if item:
        await db.delete(item)
        await db.flush()

    return {"removed": True, "product_id": product_id}
