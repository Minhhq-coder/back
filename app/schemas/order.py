from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.payment import PaymentTransactionOut


class OrderCreate(BaseModel):
    shipping_address: str = Field(..., min_length=5, max_length=255)
    payment_method: str = Field(default="cod", pattern="^(cod|qr)$")
    coupon_code: Optional[str] = Field(default=None, max_length=50)
    cart_item_ids: Optional[list[int]] = Field(default=None, min_length=1)


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
    user_id: Optional[int] = None
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
    coupon_code: Optional[str] = None
    subtotal_amount: float = 0
    discount_amount: float = 0
    total_amount: float = 0
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
    revenue: float = 0


class CategorySalesOut(BaseModel):
    category_id: Optional[int] = None
    category_name: str
    product_count: int = 0
    units_sold: int = 0
    revenue: float = 0


class InventoryProductOut(BaseModel):
    product_id: int
    product_name: str
    category_name: Optional[str] = None
    product_image: Optional[str] = None
    stock_quantity: int
    recent_units_sold: int = 0


class ProductPerformanceOut(BaseModel):
    product_id: int
    product_name: str
    category_name: Optional[str] = None
    product_image: Optional[str] = None
    views: int = 0
    units_sold: int = 0
    favorites: int = 0
    conversion_rate: float = 0


class SlowProductOut(BaseModel):
    product_id: int
    product_name: str
    category_name: Optional[str] = None
    product_image: Optional[str] = None
    stock_quantity: int
    units_sold: int = 0
    revenue: float = 0
    last_order_at: Optional[datetime] = None


class RatingDistributionOut(BaseModel):
    rating: int
    total_reviews: int


class LowRatedProductOut(BaseModel):
    product_id: int
    product_name: str
    category_name: Optional[str] = None
    product_image: Optional[str] = None
    average_rating: float = 0
    total_reviews: int = 0
    low_reviews: int = 0


class CouponPerformanceOut(BaseModel):
    code: str
    discount_type: str
    discount_value: float
    used_count: int = 0
    usage_limit: Optional[int] = None
    remaining_uses: Optional[int] = None
    end_at: Optional[datetime] = None
    is_active: bool = True
    orders_count: int = 0
    total_discount: float = 0
    revenue_after_discount: float = 0


class StatisticsOut(BaseModel):
    total_orders: int
    pending_orders: int
    approved_orders: int
    shipping_orders: int
    delivered_orders: int
    cancelled_orders: int
    total_revenue: float
    total_products: int = 0
    active_products: int = 0
    hidden_products: int = 0
    out_of_stock_products: int = 0
    low_stock_products_count: int = 0
    total_categories: int = 0
    active_coupons: int = 0
    top_products: list[ProductSalesOut] = []
    daily_orders: list[DailyOrdersOut] = []
    category_sales: list[CategorySalesOut] = []
    low_stock_products: list[InventoryProductOut] = []
    slow_products: list[SlowProductOut] = []
    top_viewed_products: list[ProductPerformanceOut] = []
    top_wishlist_products: list[ProductPerformanceOut] = []
    rating_distribution: list[RatingDistributionOut] = []
    low_rated_products: list[LowRatedProductOut] = []
    coupon_performance: list[CouponPerformanceOut] = []


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
