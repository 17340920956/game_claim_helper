from sqlalchemy.orm import Session
from app.models.base import User
from app.schemas.base import UserCreate, UserUpdate

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_wx_id(self, wx_id: str) -> User:
        return self.db.query(User).filter(User.wx_id == wx_id, User.is_del == False).first()

    def get_user_by_qq_id(self, qq_id: str) -> User:
        return self.db.query(User).filter(User.qq_id == qq_id, User.is_del == False).first()

    def create_user(self, user_create: UserCreate) -> User:
        db_user = User(**user_create.dict(exclude_unset=True))
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        db_user = self.get_user(user_id)
        if not db_user:
            return None
        
        update_data = user_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_user, key, value)
            
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def list_users(self, skip: int = 0, limit: int = 100):
        return self.db.query(User).filter(User.is_del == False).offset(skip).limit(limit).all()

    def get_user(self, user_id: int) -> User:
        return self.db.query(User).filter(User.id == user_id, User.is_del == False).first()
    
    def delete_user(self, user_id: int):
        db_user = self.get_user(user_id)
        if db_user:
            db_user.is_del = True
            self.db.commit()
            return True
        return False

    def get_all_users(self):
        return self.db.query(User).filter(User.is_del == False).all()
