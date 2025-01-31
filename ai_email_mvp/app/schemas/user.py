from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    oauth_token: str
    refresh_token: str
    google_credentials: Optional[Dict[str, Any]] = None

class UserUpdate(UserBase):
    oauth_token: Optional[str] = None
    refresh_token: Optional[str] = None
    google_credentials: Optional[Dict[str, Any]] = None

class User(UserBase):
    id: int
    oauth_token: str
    refresh_token: str
    google_credentials: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
