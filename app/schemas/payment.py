from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class PaymentTransactionOut(BaseModel):
    id: int
    order_id: int
    provider: str
    transaction_code: str
    provider_transaction_id: Optional[str] = None
    amount: float
    currency: str
    status: str
    qr_payload: Optional[str] = None
    checkout_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentStatusOut(BaseModel):
    order_id: int
    payment_method: str
    payment_status: str
    latest_payment: Optional[PaymentTransactionOut] = None


class PaymentQrCodeOut(BaseModel):
    image_data_url: str


class PaymentWebhookIn(BaseModel):
    transaction_code: str
    status: Literal["paid", "failed", "expired", "cancelled"]
    provider_transaction_id: Optional[str] = None
    raw_payload: Optional[str] = None
