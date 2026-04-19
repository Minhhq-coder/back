import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class PaymentTransactionStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    transaction_code = Column(String(100), nullable=False, unique=True, index=True)
    provider_transaction_id = Column(String(100), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="VND")
    status = Column(String(20), nullable=False, default=PaymentTransactionStatus.PENDING.value)
    qr_payload = Column(Text, nullable=True)
    checkout_url = Column(String(255), nullable=True)
    raw_payload = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    order = relationship("Order", back_populates="payments")
