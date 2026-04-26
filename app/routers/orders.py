from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models import (
    Cart,
    CartItem,
    Coupon,
    Notification,
    Order,
    OrderDetail,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Product,
    User,
)
from app.schemas import OrderCreate, OrderOut
from app.services.order_code_service import generate_unique_order_code
from app.services.coupon_service import get_coupon_by_code, validate_coupon_for_subtotal
from app.services.payment_service import (
    cancel_open_payments,
    create_payment_for_order,
    reserve_inventory_for_order,
    restore_inventory_for_order,
)

router = APIRouter(tags=["Orders"])


async def _load_order(db: AsyncSession, order_id: int) -> Order:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.details), selectinload(Order.payments))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def _clear_cart(cart: Cart, db: AsyncSession) -> None:
    for item in cart.items:
        await db.delete(item)


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_user: User = Depends(require_permission("orders:create")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.user_id == current_user.id)
    )
    cart = result.scalar_one_or_none()

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    try:
        payment_method = PaymentMethod(data.payment_method)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unsupported payment method")

    order = Order(
        order_code=await generate_unique_order_code(db),
        user_id=current_user.id,
        shipping_address=data.shipping_address.strip(),
        date_order=datetime.utcnow(),
        status=OrderStatus.PENDING.value,
        payment_method=payment_method.value,
        payment_status=(
            PaymentStatus.PENDING.value if payment_method == PaymentMethod.QR else PaymentStatus.UNPAID.value
        ),
    )
    db.add(order)
    await db.flush()

    order_subtotal = 0.0
    for item in cart.items:
        product = item.product
        if not product.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Product '{product.name}' is no longer available",
            )
        if product.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{product.name}'. Available: {product.quantity}",
            )

        db.add(
            OrderDetail(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                product_name=product.name,
                product_price=product.price,
                product_image=product.image1,
            )
        )
        order_subtotal += product.price * item.quantity

    discount_amount = 0.0
    coupon: Coupon | None = None
    coupon_code = (data.coupon_code or "").strip()
    if coupon_code:
        coupon = await get_coupon_by_code(db, coupon_code)
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found")
        discount_amount = validate_coupon_for_subtotal(coupon, order_subtotal)
        coupon.used_count += 1

    order.subtotal_amount = round(order_subtotal, 2)
    order.discount_amount = round(discount_amount, 2)
    order.total_amount = round(max(order_subtotal - discount_amount, 0), 2)
    order.coupon_code = coupon.code if coupon else None

    await db.flush()
    order = await _load_order(db, order.id)

    if payment_method == PaymentMethod.COD:
        await reserve_inventory_for_order(db, order)
        db.add(
            Notification(
                user_id=current_user.id,
                title="Äáº·t hÃ ng thÃ nh cÃ´ng",
                message=(
                    f"ÄÆ¡n hÃ ng {order.order_code} Ä‘Ã£ Ä‘Æ°á»£c táº¡o thÃ nh cÃ´ng, tá»•ng giÃ¡ trá»‹ "
                    f"{order.total_amount:,.0f} VND vÃ  sáº½ giao tá»›i Ä‘á»‹a chá»‰: {order.shipping_address}."
                ),
                order_id=order.id,
            )
        )
        db.add(
            Notification(
                target_role="admin",
                title=f"ÄÆ¡n hÃ ng má»›i {order.order_code}",
                message=(
                    f"KhÃ¡ch hÃ ng {current_user.name} ({current_user.email}) vá»«a Ä‘áº·t Ä‘Æ¡n hÃ ng "
                    f"{order.order_code}, tá»•ng giÃ¡ trá»‹ {order.total_amount:,.0f} VND, giao tá»›i: {order.shipping_address}."
                ),
                order_id=order.id,
            )
        )
    else:
        payment = await create_payment_for_order(db, order)
        db.add(
            Notification(
                user_id=current_user.id,
                title="ÄÆ¡n hÃ ng chá» thanh toÃ¡n",
                message=(
                    f"ÄÆ¡n hÃ ng {order.order_code} Ä‘Ã£ Ä‘Æ°á»£c táº¡o. Vui lÃ²ng hoÃ n táº¥t thanh toÃ¡n QR "
                    f"trÆ°á»›c {payment.expires_at.strftime('%H:%M %d/%m/%Y')}."
                ),
                order_id=order.id,
            )
        )
        db.add(
            Notification(
                target_role="admin",
                title=f"ÄÆ¡n hÃ ng má»›i chá» thanh toÃ¡n {order.order_code}",
                message=(
                    f"KhÃ¡ch hÃ ng {current_user.name} ({current_user.email}) vá»«a táº¡o Ä‘Æ¡n hÃ ng "
                    f"{order.order_code} vá»›i hÃ¬nh thá»©c thanh toÃ¡n QR, tá»•ng giÃ¡ trá»‹ {order.total_amount:,.0f} VND."
                ),
                order_id=order.id,
            )
        )

    await _clear_cart(cart, db)
    await db.flush()

    return await _load_order(db, order.id)


@router.get("/my-orders", response_model=list[OrderOut])
async def my_orders(
    order_status: str | None = Query(None, alias="status"),
    current_user: User = Depends(require_permission("orders:read")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Order)
        .options(selectinload(Order.details), selectinload(Order.payments))
        .where(Order.user_id == current_user.id)
        .order_by(Order.date_order.desc())
    )

    if order_status:
        try:
            status_enum = OrderStatus(order_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Choose from: {[s.value for s in OrderStatus]}",
            )
        query = query.where(Order.status == status_enum.value)

    result = await db.execute(query)
    return result.scalars().all()


@router.put("/my-orders/{order_id}/confirm-received", response_model=OrderOut)
async def confirm_received(
    order_id: int,
    current_user: User = Depends(require_permission("orders:confirm")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.details), selectinload(Order.payments))
        .where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.SHIPPING.value:
        raise HTTPException(
            status_code=400,
            detail="Can only confirm receipt for orders being shipped",
        )

    order.status = OrderStatus.DELIVERED.value
    if order.payment_method == PaymentMethod.COD.value and not order.is_paid:
        order.is_paid = True
        order.payment_status = PaymentStatus.PAID.value
        order.paid_at = datetime.utcnow()

    await db.flush()
    await db.refresh(order)
    return await _load_order(db, order.id)


@router.put("/my-orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(require_permission("orders:cancel")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.details), selectinload(Order.payments))
        .where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in {OrderStatus.PENDING.value, OrderStatus.APPROVED.value}:
        raise HTTPException(
            status_code=400,
            detail="Only pending or approved orders can be cancelled",
        )

    await restore_inventory_for_order(db, order)
    await cancel_open_payments(order)

    order.status = OrderStatus.CANCELLED.value
    order.is_paid = False
    if order.payment_method == PaymentMethod.QR.value:
        order.payment_status = PaymentStatus.CANCELLED.value

    await db.flush()
    await db.refresh(order)
    return await _load_order(db, order.id)
