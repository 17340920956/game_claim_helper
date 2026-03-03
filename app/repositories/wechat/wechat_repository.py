from sqlalchemy.orm import Session
from app.models.base import User

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
        # Using is_del to represent active status (0=active, 1=deleted)
        # If is_active is True, is_del should be False.
        user.is_del = not is_active
        self.db.commit()
