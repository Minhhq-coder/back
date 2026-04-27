from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CouponBase(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
    discount_type: str = Field(default="percent", pattern="^(percent|fixed)$")
    discount_value: float = Field(..., gt=0)
    min_order_value: float = Field(default=0, ge=0)
    max_discount: Optional[float] = Field(default=None, gt=0)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    usage_limit: Optional[int] = Field(default=None, ge=1)
    is_active: bool = True


class CouponCreate(CouponBase):
    pass


class CouponUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
    discount_type: Optional[str] = Field(default=None, pattern="^(percent|fixed)$")
    discount_value: Optional[float] = Field(default=None, gt=0)
    min_order_value: Optional[float] = Field(default=None, ge=0)
    max_discount: Optional[float] = Field(default=None, gt=0)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    usage_limit: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class CouponOut(CouponBase):
    id: int
    code: str
    used_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CouponValidateIn(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    subtotal: float = Field(..., ge=0)


class CouponValidateOut(BaseModel):
    code: str
    discount_amount: float
    subtotal: float
    total: float
    message: str
