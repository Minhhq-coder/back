from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.payment import PaymentTransactionOut


class OrderCreate(BaseModel):
    shipping_address: str = Field(..., min_length=5, max_length=255)
    payment_method: str = Field(default="cod", pattern="^(cod|qr)$")


class OrderDetailOut(BaseModel):
    id: int
    product_id: Optional[int] = None
    quantity: int
    product_name: str
    product_price: float
    product_image: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    order_code: Optional[str] = None
    user_id: int
    shipping_address: str
    date_order: datetime
    date_ship: Optional[datetime] = None
    is_paid: bool
    status: str
    payment_method: str
    payment_status: str
    payment_provider: Optional[str] = None
    payment_transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    details: list[OrderDetailOut] = []
    latest_payment: Optional[PaymentTransactionOut] = None

    model_config = {"from_attributes": True}


# ── Statistics ────────────────────────────────────────────────────────────────

class StatisticsQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProductSalesOut(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    category_name: Optional[str] = None
    product_image: Optional[str] = None
    units_sold: int
    revenue: float


class DailyOrdersOut(BaseModel):
    order_date: date
    total_orders: int


class StatisticsOut(BaseModel):
    total_orders: int
    pending_orders: int
    approved_orders: int
    shipping_orders: int
    delivered_orders: int
    cancelled_orders: int
    total_revenue: float
    top_products: list[ProductSalesOut] = []
    daily_orders: list[DailyOrdersOut] = []


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
