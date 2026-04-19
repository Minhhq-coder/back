from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    address: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    birth_date: Optional[date] = None
    is_confirm: bool
    user_type_id: int

    model_config = {"from_attributes": True}


class PermissionOut(BaseModel):
    code: str
    description: str

    model_config = {"from_attributes": True}


class UserProfileOut(UserOut):
    role: str
    permissions: list[PermissionOut]


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)


class AvatarUploadResponse(BaseModel):
    avatar: str


class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    avatar: Optional[str] = Field(None, max_length=255)
    is_confirm: Optional[bool] = None
    user_type_id: Optional[int] = None


class AdminUserOut(UserOut):
    role: str
    permissions: list[PermissionOut]
    created_at: datetime
    last_login_at: Optional[datetime] = None
