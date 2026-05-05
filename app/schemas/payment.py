from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel
from pydantic import ConfigDict


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
    qr_url: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    transfer_content: Optional[str] = None
    expires_at: Optional[datetime] = None


class PaymentWebhookIn(BaseModel):
    transaction_code: str
    status: Literal["paid", "failed", "expired", "cancelled"]
    provider_transaction_id: Optional[str] = None
    raw_payload: Optional[str] = None


class SepayWebhookIn(BaseModel):
    id: int | str
    gateway: Optional[str] = None
    transactionDate: Optional[str] = None
    accountNumber: Optional[str] = None
    code: Optional[str] = None
    content: Optional[str] = None
    transferType: str
    transferAmount: float
    accumulated: Optional[float] = None
    subAccount: Optional[str] = None
    referenceCode: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(extra="allow")
