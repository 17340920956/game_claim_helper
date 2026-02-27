from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models import ContactType, PushStatus, ConfirmationStatus


class UserBase(BaseModel):
    epic_account: str
    contact_type: ContactType
    contact_id: str


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class GameInfo(BaseModel):
    title: str
    slug: str
    url: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    thumbnail: Optional[str] = None


class PushLogBase(BaseModel):
    user_id: int
    game_slug: str
    game_title: str
    contact_type: ContactType
    contact_id: str
    status: PushStatus
    message: Optional[str] = None
    error_msg: Optional[str] = None
    is_next_week: bool = False


class PushLogResponse(PushLogBase):
    id: int
    confirmation_status: ConfirmationStatus
    confirmation_time: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConfirmationRequest(BaseModel):
    user_id: int
    game_slug: str
    action: str


class PushRequest(BaseModel):
    user_id: int
    game_slug: str
