"""Pydantic schemas for User entity."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "free"
    plan: str = "free"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    plan: Optional[str] = None
    status: Optional[str] = None


class UserRead(UserBase):
    id: uuid.UUID
    status: str
    email_verified: bool
    totp_enabled: bool
    registration_date: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
