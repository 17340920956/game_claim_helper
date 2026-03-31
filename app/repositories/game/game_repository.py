from sqlalchemy.orm import Session
from app.models.base import FreeGame
from app.schemas.base import FreeGameCreate
from datetime import datetime, timezone


class GameRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _now_utc():
        return datetime.now(timezone.utc)

    def get_game_by_name(self, name: str) -> FreeGame:
        return self.db.query(FreeGame).filter(FreeGame.name == name).first()

    def create_game(self, game_create: FreeGameCreate) -> FreeGame:
        db_game = FreeGame(**game_create.dict())
        self.db.add(db_game)
        self.db.commit()
        self.db.refresh(db_game)
        return db_game

    def update_game(self, game: FreeGame, game_data: dict) -> FreeGame:
        for key, value in game_data.items():
            if hasattr(game, key) and value is not None:
                setattr(game, key, value)
        self.db.commit()
        self.db.refresh(game)
        return game

    def get_active_games(self) -> list[FreeGame]:
        now = self._now_utc()
        return self.db.query(FreeGame).filter(
            FreeGame.start_time <= now,
            FreeGame.end_time >= now
        ).all()

    def get_upcoming_games(self) -> list[FreeGame]:
        now = self._now_utc()
        return self.db.query(FreeGame).filter(
            FreeGame.start_time > now
        ).all()

    def get_expired_games(self) -> list[FreeGame]:
        now = self._now_utc()
        return self.db.query(FreeGame).filter(
            FreeGame.end_time < now
        ).all()

    def get_all_games(self) -> list[FreeGame]:
        return self.db.query(FreeGame).all()

    def get_game(self, game_id: int) -> FreeGame:
        return self.db.query(FreeGame).filter(FreeGame.id == game_id).first()

    def get_by_id(self, game_id: int) -> FreeGame:
        return self.db.query(FreeGame).filter(FreeGame.id == game_id).first()
