from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Product ───────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    external_id: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    name: str = Field(..., min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=255)
    category_id: int
    subcategory: Optional[str] = Field(None, max_length=100)
    image1: Optional[str] = None
    image2: Optional[str] = None
    image3: Optional[str] = None
    image_url: Optional[str] = None
    price: float = Field(..., gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    currency: str = Field(default="VND", max_length=10)
    volume: Optional[str] = Field(None, max_length=100)
    quantity: int = Field(..., ge=0)
    stock_status: str = Field(default="unknown", max_length=50)
    description: Optional[str] = None
    usage: Optional[str] = None
    skin_type: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    product_url: Optional[str] = None
    source: Optional[str] = Field(None, max_length=50)
    last_updated: Optional[date] = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    external_id: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=255)
    category_id: Optional[int] = None
    subcategory: Optional[str] = Field(None, max_length=100)
    image1: Optional[str] = None
    image2: Optional[str] = None
    image3: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=10)
    volume: Optional[str] = Field(None, max_length=100)
    quantity: Optional[int] = Field(None, ge=0)
    stock_status: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    usage: Optional[str] = None
    skin_type: Optional[list[str]] = None
    concerns: Optional[list[str]] = None
    ingredients: Optional[list[str]] = None
    benefits: Optional[list[str]] = None
    product_url: Optional[str] = None
    source: Optional[str] = Field(None, max_length=50)
    last_updated: Optional[date] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    external_id: Optional[str] = None
    slug: Optional[str] = None
    name: str
    brand: Optional[str] = None
    category_id: int
    subcategory: Optional[str] = None
    image1: Optional[str] = None
    image2: Optional[str] = None
    image3: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    currency: str
    volume: Optional[str] = None
    quantity: int
    stock_status: str
    description: Optional[str] = None
    usage: Optional[str] = None
    skin_type: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    product_url: Optional[str] = None
    source: Optional[str] = None
    last_updated: Optional[date] = None
    view_count: int
    purchased_count: int
    is_active: bool

    model_config = {"from_attributes": True}


class ProductBrief(BaseModel):
    id: int
    external_id: Optional[str] = None
    slug: Optional[str] = None
    name: str
    brand: Optional[str] = None
    image1: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    currency: str = "VND"
    volume: Optional[str] = None
    quantity: int
    purchased_count: int
    stock_status: str = "unknown"

    model_config = {"from_attributes": True}
