from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PAYMENT_EXPIRE_MINUTES, PAYMENT_PROVIDER
from app.models import (
    Notification,
    Order,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
    Product,
)


def calculate_order_total(order: Order) -> float:
    return float(sum(detail.product_price * detail.quantity for detail in order.details))


def build_qr_payload(order: Order, amount: float, transaction_code: str) -> str:
    return (
        f"provider={PAYMENT_PROVIDER}"
        f"&transaction={transaction_code}"
        f"&order={order.order_code or order.id}"
        f"&amount={amount:,.0f}"
        f"&currency=VND"
    )


async def create_payment_for_order(db: AsyncSession, order: Order) -> PaymentTransaction:
    amount = calculate_order_total(order)
    transaction_code = f"PAY-{uuid4().hex[:12].upper()}"
    expires_at = datetime.utcnow() + timedelta(minutes=PAYMENT_EXPIRE_MINUTES)

    payment = PaymentTransaction(
        order_id=order.id,
        provider=PAYMENT_PROVIDER,
        transaction_code=transaction_code,
        amount=amount,
        currency="VND",
        status=PaymentTransactionStatus.PENDING.value,
        qr_payload=build_qr_payload(order, amount, transaction_code),
        expires_at=expires_at,
    )
    db.add(payment)

    order.payment_method = PaymentMethod.QR.value
    order.payment_status = PaymentStatus.PENDING.value
    order.payment_provider = PAYMENT_PROVIDER
    order.payment_transaction_id = transaction_code

    await db.flush()
    return payment


async def reserve_inventory_for_order(db: AsyncSession, order: Order) -> None:
    if order.inventory_reserved:
        return

    detail_product_ids = [detail.product_id for detail in order.details]
    if not detail_product_ids:
        order.inventory_reserved = True
        return

    products_result = await db.execute(select(Product).where(Product.id.in_(detail_product_ids)))
    products_by_id = {product.id: product for product in products_result.scalars().all()}

    for detail in order.details:
        product = products_by_id.get(detail.product_id)
        if not product or not product.is_active:
            raise ValueError(f"Product '{detail.product_name}' is no longer available")
        if product.quantity < detail.quantity:
            raise ValueError(f"Insufficient stock for '{detail.product_name}'")

    for detail in order.details:
        product = products_by_id[detail.product_id]
        product.quantity -= detail.quantity
        product.purchased_count += detail.quantity

    order.inventory_reserved = True


async def restore_inventory_for_order(db: AsyncSession, order: Order) -> None:
    if not order.inventory_reserved:
        return

    detail_product_ids = [detail.product_id for detail in order.details]
    if not detail_product_ids:
        order.inventory_reserved = False
        return

    products_result = await db.execute(select(Product).where(Product.id.in_(detail_product_ids)))
    products_by_id = {product.id: product for product in products_result.scalars().all()}

    for detail in order.details:
        product = products_by_id.get(detail.product_id)
        if product:
            product.quantity += detail.quantity
            product.purchased_count = max(0, product.purchased_count - detail.quantity)

    order.inventory_reserved = False


async def mark_payment_status(
    db: AsyncSession,
    payment: PaymentTransaction,
    new_status: str,
    provider_transaction_id: str | None = None,
    raw_payload: str | None = None,
) -> Order:
    order = payment.order

    if payment.status == new_status:
        return order

    if provider_transaction_id:
        payment.provider_transaction_id = provider_transaction_id
    if raw_payload:
        payment.raw_payload = raw_payload

    if new_status == PaymentTransactionStatus.PAID.value:
        await reserve_inventory_for_order(db, order)
        payment.status = PaymentTransactionStatus.PAID.value
        payment.paid_at = datetime.utcnow()
        order.payment_status = PaymentStatus.PAID.value
        order.is_paid = True
        order.paid_at = payment.paid_at
        db.add(
            Notification(
                user_id=order.user_id,
                title="Thanh toán thành công",
                message=f"Đơn hàng {order.order_code or order.id} đã được thanh toán thành công.",
                order_id=order.id,
            )
        )
        db.add(
            Notification(
                target_role="admin",
                title=f"Thanh toán thành công {order.order_code or order.id}",
                message=f"Đơn hàng {order.order_code or order.id} đã được thanh toán thành công và sẵn sàng xử lý.",
                order_id=order.id,
            )
        )
    elif new_status == PaymentTransactionStatus.FAILED.value:
        payment.status = PaymentTransactionStatus.FAILED.value
        order.payment_status = PaymentStatus.FAILED.value
    elif new_status == PaymentTransactionStatus.EXPIRED.value:
        payment.status = PaymentTransactionStatus.EXPIRED.value
        order.payment_status = PaymentStatus.EXPIRED.value
    elif new_status == PaymentTransactionStatus.CANCELLED.value:
        payment.status = PaymentTransactionStatus.CANCELLED.value
        order.payment_status = PaymentStatus.CANCELLED.value

    order.payment_transaction_id = payment.transaction_code
    order.payment_provider = payment.provider
    await db.flush()
    return order


async def cancel_open_payments(order: Order) -> None:
    for payment in order.payments:
        if payment.status == PaymentTransactionStatus.PENDING.value:
            payment.status = PaymentTransactionStatus.CANCELLED.value


def can_retry_payment(order: Order) -> bool:
    return (
        order.payment_method == PaymentMethod.QR.value
        and order.payment_status in {
            PaymentStatus.FAILED.value,
            PaymentStatus.EXPIRED.value,
            PaymentStatus.CANCELLED.value,
        }
        and order.status not in {OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value}
    )
