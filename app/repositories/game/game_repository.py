from sqlalchemy.orm import Session
from app.models.base import FreeGame
from app.schemas.base import FreeGameCreate
from datetime import datetime

class GameRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_game_by_name(self, name: str) -> FreeGame:
        return self.db.query(FreeGame).filter(FreeGame.name == name).first()

    def create_game(self, game_create: FreeGameCreate) -> FreeGame:
        db_game = FreeGame(**game_create.dict())
        self.db.add(db_game)
        self.db.commit()
        self.db.refresh(db_game)
        return db_game

    def get_active_games(self) -> list[FreeGame]:
        now = datetime.now()
        return self.db.query(FreeGame).filter(
            FreeGame.start_time <= now,
            FreeGame.end_time >= now
        ).all()
    
    def get_upcoming_games(self) -> list[FreeGame]:
        now = datetime.now()
        return self.db.query(FreeGame).filter(
            FreeGame.start_time > now
        ).all()

    def get_game(self, game_id: int) -> FreeGame:
        return self.db.query(FreeGame).filter(FreeGame.id == game_id).first()
