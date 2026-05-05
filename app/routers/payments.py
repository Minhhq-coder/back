from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import (
    ENABLE_MOCK_PAYMENTS,
    PAYMENT_WEBHOOK_SECRET,
    SEPAY_ACCOUNT_NAME,
    SEPAY_ACCOUNT_NUMBER,
    SEPAY_BANK_NAME,
    SEPAY_WEBHOOK_API_KEY,
)
from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin, require_permission
from app.models import (
    Order,
    OrderStatus,
    PaymentStatus,
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
    SepayWebhookIn,
)
from app.services.payment_service import (
    can_retry_payment,
    create_payment_for_order,
    get_payment_qr_image,
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


def _extract_apikey(authorization: str | None) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.strip().partition(" ")
    if scheme.lower() != "apikey" or not token:
        return None
    return token.strip()


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
        image_data_url = get_payment_qr_image(payment)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QR code generator is not available",
        ) from error

    is_sepay_payment = payment.provider == "sepay"
    return PaymentQrCodeOut(
        image_data_url=image_data_url,
        qr_url=image_data_url if is_sepay_payment else None,
        bank_name=SEPAY_BANK_NAME if is_sepay_payment else None,
        account_number=SEPAY_ACCOUNT_NUMBER if is_sepay_payment else None,
        account_name=SEPAY_ACCOUNT_NAME if is_sepay_payment else None,
        amount=payment.amount,
        currency=payment.currency,
        transfer_content=payment.qr_payload,
        expires_at=payment.expires_at,
    )


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


@router.post("/sepay/webhook")
async def sepay_payment_webhook(
    data: SepayWebhookIn,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not SEPAY_WEBHOOK_API_KEY or _extract_apikey(authorization) != SEPAY_WEBHOOK_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid SePay webhook API key")

    if data.transferType != "in":
        return {"success": True}

    if SEPAY_ACCOUNT_NUMBER and data.accountNumber and data.accountNumber != SEPAY_ACCOUNT_NUMBER:
        raise HTTPException(status_code=400, detail="Unexpected SePay account number")

    payment_code = (data.code or "").strip()
    if not payment_code:
        return {"success": True}

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.details), selectinload(Order.payments))
        .where(Order.order_code == payment_code)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for SePay payment code")

    if order.payment_status == PaymentStatus.PAID.value:
        return {"success": True}

    if float(data.transferAmount) < float(order.total_amount):
        raise HTTPException(status_code=400, detail="SePay transfer amount is lower than order total")

    payment = next(
        (
            item
            for item in order.payments
            if item.provider == "sepay" and item.status == PaymentTransactionStatus.PENDING.value
        ),
        None,
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Pending SePay payment transaction not found")

    await mark_payment_status(
        db,
        payment,
        PaymentTransactionStatus.PAID.value,
        provider_transaction_id=data.referenceCode or str(data.id),
        raw_payload=data.model_dump_json(),
    )

    return {"success": True}


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
