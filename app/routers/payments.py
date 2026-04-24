from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import ENABLE_MOCK_PAYMENTS, PAYMENT_WEBHOOK_SECRET
from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin, require_permission
from app.models import (
    Order,
    OrderStatus,
    PaymentMethod,
    PaymentTransaction,
    PaymentTransactionStatus,
    User,
)
from app.schemas import (
    PaymentQrCodeOut,
    PaymentStatusOut,
    PaymentTransactionOut,
    PaymentWebhookIn,
)
from app.services.payment_service import (
    build_qr_image_data_url,
    can_retry_payment,
    create_payment_for_order,
    mark_payment_status,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


async def _load_user_order(db: AsyncSession, user_id: int, order_id: int) -> Order:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.details), selectinload(Order.payments))
        .where(Order.id == order_id, Order.user_id == user_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _is_admin(user: User) -> bool:
    permissions = {permission.code for permission in getattr(user.user_type, "permissions", [])}
    return "admin:access" in permissions


async def _load_accessible_payment(
    db: AsyncSession,
    current_user: User,
    transaction_code: str,
) -> PaymentTransaction:
    result = await db.execute(
        select(PaymentTransaction)
        .options(
            selectinload(PaymentTransaction.order).selectinload(Order.details),
            selectinload(PaymentTransaction.order).selectinload(Order.payments),
        )
        .where(PaymentTransaction.transaction_code == transaction_code)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment transaction not found")

    if payment.order.user_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this payment")

    return payment


@router.post("/create-from-order/{order_id}", response_model=PaymentTransactionOut, status_code=status.HTTP_201_CREATED)
async def create_payment_from_order(
    order_id: int,
    current_user: User = Depends(require_permission("payments:create")),
    db: AsyncSession = Depends(get_db),
):
    order = await _load_user_order(db, current_user.id, order_id)

    if order.payment_method != PaymentMethod.QR.value:
        raise HTTPException(status_code=400, detail="This order does not use QR payment")

    if order.status == OrderStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Cancelled orders cannot create a new payment")

    if not can_retry_payment(order):
        raise HTTPException(status_code=400, detail="This order is not eligible for a new payment attempt")

    payment = await create_payment_for_order(db, order)
    await db.flush()
    return payment


@router.get("/order/{order_id}", response_model=PaymentStatusOut)
async def get_payment_status(
    order_id: int,
    current_user: User = Depends(require_permission("payments:read")),
    db: AsyncSession = Depends(get_db),
):
    order = await _load_user_order(db, current_user.id, order_id)
    return PaymentStatusOut(
        order_id=order.id,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        latest_payment=order.latest_payment,
    )


@router.get("/{transaction_code}/qr", response_model=PaymentQrCodeOut)
async def get_payment_qr_code(
    transaction_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await _load_accessible_payment(db, current_user, transaction_code)
    if not payment.qr_payload:
        raise HTTPException(status_code=404, detail="QR payload not found")

    try:
        image_data_url = build_qr_image_data_url(payment.qr_payload)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QR code generator is not available",
        ) from error

    return PaymentQrCodeOut(image_data_url=image_data_url)


@router.post("/webhook", response_model=PaymentStatusOut)
async def payment_webhook(
    data: PaymentWebhookIn,
    x_payment_webhook_secret: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    if x_payment_webhook_secret != PAYMENT_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    result = await db.execute(
        select(PaymentTransaction)
        .options(
            selectinload(PaymentTransaction.order).selectinload(Order.details),
            selectinload(PaymentTransaction.order).selectinload(Order.payments),
        )
        .where(PaymentTransaction.transaction_code == data.transaction_code)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment transaction not found")

    order = await mark_payment_status(
        db,
        payment,
        data.status,
        provider_transaction_id=data.provider_transaction_id,
        raw_payload=data.raw_payload,
    )

    return PaymentStatusOut(
        order_id=order.id,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        latest_payment=order.latest_payment,
    )


@router.post("/mock/{transaction_code}/paid", response_model=PaymentStatusOut)
async def mock_mark_paid(
    transaction_code: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if not ENABLE_MOCK_PAYMENTS:
        raise HTTPException(status_code=403, detail="Mock payments are disabled")

    result = await db.execute(
        select(PaymentTransaction)
        .options(
            selectinload(PaymentTransaction.order).selectinload(Order.details),
            selectinload(PaymentTransaction.order).selectinload(Order.payments),
        )
        .where(PaymentTransaction.transaction_code == transaction_code)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment transaction not found")
    if payment.provider != "mock_qr":
        raise HTTPException(status_code=400, detail="This payment does not use the mock provider")

    order = await mark_payment_status(db, payment, PaymentTransactionStatus.PAID.value)
    return PaymentStatusOut(
        order_id=order.id,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        latest_payment=order.latest_payment,
    )
