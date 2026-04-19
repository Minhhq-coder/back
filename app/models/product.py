from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, nullable=True, index=True)
    slug = Column(String(255), unique=True, nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    brand = Column(String(255), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    subcategory = Column(String(100), nullable=True)
    image1 = Column(String(255), nullable=True)
    image2 = Column(String(255), nullable=True)
    image3 = Column(String(255), nullable=True)
    image_url = Column(String(500), nullable=True)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    currency = Column(String(10), nullable=False, default="VND")
    volume = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=False, default=0)
    stock_status = Column(String(50), nullable=False, default="unknown")
    description = Column(Text, nullable=True)
    usage = Column(Text, nullable=True)
    skin_type = Column(JSON, nullable=False, default=list)
    concerns = Column(JSON, nullable=False, default=list)
    ingredients = Column(JSON, nullable=False, default=list)
    benefits = Column(JSON, nullable=False, default=list)
    product_url = Column(String(500), nullable=True)
    source = Column(String(50), nullable=True)
    last_updated = Column(Date, nullable=True)
    view_count = Column(Integer, default=0)
    purchased_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    category = relationship("Category", back_populates="products")
    cart_items = relationship("CartItem", back_populates="product")
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")
