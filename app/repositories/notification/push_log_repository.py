from sqlalchemy.orm import Session
from app.models.base import PushLog
from app.schemas.base import PushLogCreate

class PushLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_log(self, log_create: PushLogCreate) -> PushLog:
        log = PushLog(**log_create.dict())
        self.db.add(log)
        self.db.commit() 
        self.db.refresh(log)
        return log

    def list_logs(self, skip: int = 0, limit: int = 100):
        return self.db.query(PushLog).order_by(PushLog.push_time.desc()).offset(skip).limit(limit).all()

    def get_user_logs(self, user_id: int):
        return self.db.query(PushLog).filter(PushLog.user_id == user_id).order_by(PushLog.push_time.desc()).all()

    def has_user_been_notified(self, user_id: int, game_id: int) -> bool:
        return self.db.query(PushLog).filter(
            PushLog.user_id == user_id,
            PushLog.game_id == game_id,
            PushLog.status == True
        ).first() is not None
