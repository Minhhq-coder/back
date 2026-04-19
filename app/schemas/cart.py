from pydantic import BaseModel, Field

from app.schemas.product import ProductBrief


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductBrief

    model_config = {"from_attributes": True}


class CartOut(BaseModel):
    id: int
    items: list[CartItemOut] = []

    model_config = {"from_attributes": True}
