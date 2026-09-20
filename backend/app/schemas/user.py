from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    badge_number: Optional[str] = None
    department: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    supabase_user_id: UUID

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    badge_number: Optional[str] = None
    department: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: UUID
    supabase_user_id: UUID
    email_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)
