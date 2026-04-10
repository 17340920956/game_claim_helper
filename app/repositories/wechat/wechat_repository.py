from sqlalchemy.orm import Session
from app.models.base import User
from app.core.crypto import encrypt_password, decrypt_password


class WeChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_openid(self, openid: str) -> User:
        return self.db.query(User).filter(
            User.wx_id == openid,
            User.is_del == False
        ).first()

    def create_user(self, openid: str) -> User:
        user = User(
            wx_id=openid,
            is_del=False
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user_active_status(self, user: User, is_active: bool):
        user.is_del = not is_active
        self.db.commit()

    def update_user_epic_account(self, user: User, email: str = None, password: str = None):
        """更新用户的 Epic 账号信息（密码加密存储）"""
        user.epic_email = email
        user.epic_password = encrypt_password(password) if password else None
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user_device_auth(self, user: User, account_id: str = None,
                                 device_id: str = None, device_secret: str = None,
                                 email: str = None, refresh_token: str = None):
        """更新用户的 Epic 认证信息（支持 Device Auth 和 Refresh Token）"""
        if account_id:
            user.epic_id = account_id
        if device_id:
            user.epic_device_id = device_id
        if device_secret:
            user.epic_device_secret = encrypt_password(device_secret)
        if refresh_token:
            user.epic_refresh_token = encrypt_password(refresh_token)
        if email:
            user.epic_email = email
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user_refresh_token(self, user: User, refresh_token: str):
        """更新用户的 Epic Refresh Token"""
        user.epic_refresh_token = encrypt_password(refresh_token)
        self.db.commit()
        self.db.refresh(user)
        return user

    def clear_user_epic_account(self, user: User):
        """清除用户所有 Epic 相关信息"""
        user.epic_email = None
        user.epic_password = None
        user.epic_id = None
        user.epic_device_id = None
        user.epic_device_secret = None
        user.epic_refresh_token = None
        user.epic_token = None
        user.token_expired_at = None
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_epic_password(self, user: User) -> str:
        """获取解密后的 Epic 密码"""
        if not user.epic_password:
            return ""
        return decrypt_password(user.epic_password)
