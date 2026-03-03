from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, BigInteger, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class User(Base):
    __tablename__ = "user"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='用户ID，主键')
    wx_id = Column(String(64), unique=True, nullable=True, comment='微信号')
    qq_id = Column(String(64), unique=True, nullable=True, comment='QQ号')
    epic_id = Column(String(64), nullable=True, comment='Epic账号ID')
    epic_email = Column(String(128), nullable=True, comment='Epic账号邮箱')
    epic_password = Column(String(256), nullable=True, comment='加密存储的Epic密码')
    epic_token = Column(String(512), nullable=True, comment='Epic授权Token')
    token_expired_at = Column(DateTime, nullable=True, comment='Token过期时间')
    is_del = Column(Boolean, default=False, comment='软删除标记，0=有效，1=删除')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    push_logs = relationship("PushLog", back_populates="user")

class FreeGame(Base):
    __tablename__ = "free_game"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='游戏ID，主键')
    name = Column(String(128), nullable=False, index=True, comment='游戏名称')
    start_time = Column(DateTime, nullable=False, comment='免费开始时间')
    end_time = Column(DateTime, nullable=False, comment='免费结束时间')
    image_url = Column(String(256), nullable=True, comment='封面图片链接')
    link = Column(String(256), nullable=True, comment='Epic游戏页面链接')
    note = Column(String(256), nullable=True, comment='备注')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    push_logs = relationship("PushLog", back_populates="game")

class PushLog(Base):
    __tablename__ = "push_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='日志ID，主键')
    user_id = Column(BigInteger, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True, comment='关联用户ID')
    game_id = Column(BigInteger, ForeignKey('free_game.id', ondelete='CASCADE'), nullable=False, index=True, comment='关联游戏ID')
    push_time = Column(DateTime, server_default=func.now(), comment='推送时间')
    status = Column(Boolean, default=False, comment='推送状态，0=失败，1=成功')
    note = Column(String(256), nullable=True, comment='备注')

    user = relationship("User", back_populates="push_logs")
    game = relationship("FreeGame", back_populates="push_logs")
