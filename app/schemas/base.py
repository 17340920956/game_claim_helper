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

    @classmethod
    def model_validate(cls, obj):
        """隐藏敏感字段"""
        data = {
            "id": obj.id,
            "wx_id": obj.wx_id,
            "qq_id": obj.qq_id,
            "epic_id": obj.epic_id,
            "epic_email": obj.epic_email,
            "epic_password": None,
            "epic_token": None,
            "token_expired_at": obj.token_expired_at,
            "is_del": obj.is_del,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }
        return cls(**data)

# ==========================
# PushLog Schemas
# ==========================
class PushLogBase(BaseModel):
    user_id: int
    game_name: str
    game_slug: Optional[str] = None
    status: bool
    is_next_week: bool = False
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
# 如果需要其他请求schema可以在此添加
