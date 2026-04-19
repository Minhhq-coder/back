from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models import User, Cart, CartItem, Product
from app.schemas import CartOut, CartItemAdd, CartItemUpdate, CartItemOut

router = APIRouter(prefix="/cart", tags=["Cart"])


async def _get_or_create_cart(user: User, db: AsyncSession) -> Cart:
    """Get user's cart or create one if it doesn't exist."""
    result = await db.execute(
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.user_id == user.id)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()
        await db.refresh(cart, attribute_names=["items"])
    return cart


@router.get("", response_model=CartOut)
async def get_cart(
    current_user: User = Depends(require_permission("cart:read")),
    db: AsyncSession = Depends(get_db),
):
    """Xem thông tin giỏ hàng."""
    cart = await _get_or_create_cart(current_user, db)
    return cart


@router.post("/items", response_model=CartItemOut, status_code=status.HTTP_201_CREATED)
async def add_cart_item(
    data: CartItemAdd,
    current_user: User = Depends(require_permission("cart:write")),
    db: AsyncSession = Depends(get_db),
):
    """Thêm sản phẩm vào giỏ (check tồn kho trước khi thêm)."""
    # Check product exists and is active
    result = await db.execute(select(Product).where(Product.id == data.product_id))
    product = result.scalar_one_or_none()
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found or inactive")

    # Check stock
    if product.quantity < data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {product.quantity}",
        )

    cart = await _get_or_create_cart(current_user, db)

    # Check if item already in cart → update quantity
    result = await db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == data.product_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        new_qty = existing.quantity + data.quantity
        if product.quantity < new_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {product.quantity}",
            )
        existing.quantity = new_qty
        await db.flush()
        await db.refresh(existing, attribute_names=["product"])
        return existing

    item = CartItem(cart_id=cart.id, product_id=data.product_id, quantity=data.quantity)
    db.add(item)
    await db.flush()
    await db.refresh(item, attribute_names=["product"])
    return item


@router.put("/items/{item_id}", response_model=CartItemOut)
async def update_cart_item(
    item_id: int,
    data: CartItemUpdate,
    current_user: User = Depends(require_permission("cart:write")),
    db: AsyncSession = Depends(get_db),
):
    """Cập nhật số lượng sản phẩm trong giỏ."""
    cart = await _get_or_create_cart(current_user, db)

    result = await db.execute(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Check stock
    product = item.product
    if product.quantity < data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {product.quantity}",
        )

    item.quantity = data.quantity
    await db.flush()
    await db.refresh(item, attribute_names=["product"])
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart_item(
    item_id: int,
    current_user: User = Depends(require_permission("cart:write")),
    db: AsyncSession = Depends(get_db),
):
    """Xóa sản phẩm khỏi giỏ."""
    cart = await _get_or_create_cart(current_user, db)

    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await db.delete(item)
    await db.flush()
