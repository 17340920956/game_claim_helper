from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from db.connection import Base
import enum


class ContactType(enum.Enum):
    wechat_official = "wechat_official"
    qq = "qq"


class PushStatus(enum.Enum):
    success = "success"
    failed = "failed"


class ConfirmationStatus(enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    claimed = "claimed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    epic_account = Column(String(100), nullable=False)
    contact_type = Column(SQLEnum(ContactType), nullable=False)
    contact_id = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class PushLog(Base):
    __tablename__ = "push_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    game_slug = Column(String(100), nullable=False)
    game_title = Column(String(100), nullable=False)
    contact_type = Column(SQLEnum(ContactType), nullable=False)
    contact_id = Column(String(50), nullable=False)
    status = Column(SQLEnum(PushStatus), nullable=False)
    message = Column(Text, nullable=True)
    error_msg = Column(Text, nullable=True)
    confirmation_status = Column(
        SQLEnum(ConfirmationStatus), 
        default=ConfirmationStatus.pending
    )
    confirmation_time = Column(DateTime, nullable=True)
    is_next_week = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
