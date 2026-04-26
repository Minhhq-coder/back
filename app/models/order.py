import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SHIPPING = "shipping"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    COD = "cod"
    QR = "qr"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(20), unique=True, index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    shipping_address = Column(String(255), nullable=False, default="")
    date_order = Column(DateTime, default=datetime.utcnow)
    date_ship = Column(DateTime, nullable=True)
    is_paid = Column(Boolean, default=False)
    status = Column(String(20), default=OrderStatus.PENDING.value, nullable=False)
    payment_method = Column(String(20), default=PaymentMethod.COD.value, nullable=False)
    payment_status = Column(String(20), default=PaymentStatus.UNPAID.value, nullable=False)
    payment_provider = Column(String(50), nullable=True)
    payment_transaction_id = Column(String(100), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    inventory_reserved = Column(Boolean, default=False, nullable=False)
    coupon_code = Column(String(50), nullable=True)
    subtotal_amount = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False, default=0)

    user = relationship("User", back_populates="orders")
    details = relationship("OrderDetail", back_populates="order", cascade="all, delete-orphan")
    payments = relationship(
        "PaymentTransaction",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="desc(PaymentTransaction.created_at)",
    )

    @property
    def latest_payment(self):
        return self.payments[0] if self.payments else None


class OrderDetail(Base):
    __tablename__ = "order_details"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False)
    product_name = Column(String(200), nullable=False)
    product_price = Column(Float, nullable=False)
    product_image = Column(String(255), nullable=True)

    order = relationship("Order", back_populates="details")
    product = relationship("Product")
