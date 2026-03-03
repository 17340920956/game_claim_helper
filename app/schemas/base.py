from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ==========================
# User Schemas
# ==========================
class UserBase(BaseModel):
    wx_id: Optional[str] = None
    qq_id: Optional[str] = None
    epic_id: Optional[str] = None
    epic_email: Optional[str] = None
    epic_password: Optional[str] = None
    epic_token: Optional[str] = None
    token_expired_at: Optional[datetime] = None
    is_del: Optional[bool] = False

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ==========================
# FreeGame Schemas
# ==========================
class FreeGameBase(BaseModel):
    name: str
    start_time: datetime
    end_time: datetime
    image_url: Optional[str] = None
    link: Optional[str] = None
    note: Optional[str] = None

class FreeGameCreate(FreeGameBase):
    pass

class FreeGameResponse(FreeGameBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ==========================
# PushLog Schemas
# ==========================
class PushLogBase(BaseModel):
    user_id: int
    game_id: int
    status: bool
    note: Optional[str] = None

class PushLogCreate(PushLogBase):
    pass

class PushLogResponse(PushLogBase):
    id: int
    push_time: datetime

    class Config:
        from_attributes = True

# ==========================
# API Request Schemas
# ==========================
class PushRequest(BaseModel):
    user_id: int
    game_id: int
