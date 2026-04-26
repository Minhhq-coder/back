from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserType(Base):
    __tablename__ = "user_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # "admin" | "customer"

    users = relationship("User", back_populates="user_type")
    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="user_types",
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    avatar = Column(String(255), nullable=True)
    birth_date = Column(Date, nullable=True)
    google_sub = Column(String(255), unique=True, nullable=True, index=True)
    is_confirm = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    user_type_id = Column(Integer, ForeignKey("user_types.id"), nullable=False)

    user_type = relationship("UserType", back_populates="users")
    cart = relationship("Cart", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", passive_deletes=True)
    reviews = relationship("ProductReview", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    revoked_tokens = relationship("RevokedToken", back_populates="user", cascade="all, delete-orphan")
    wishlist_items = relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan")
