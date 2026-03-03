from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.base import FreeGameResponse
from app.core.security import verify_admin_access
from app.services.game.scraper_service import fetch_and_store_games
from app.repositories.game.game_repository import GameRepository

router = APIRouter(tags=["Games"])

@router.get("/games/current", response_model=List[FreeGameResponse])
def get_current_games(db: Session = Depends(get_db)):
    repo = GameRepository(db)
    return repo.get_active_games()

@router.get("/games/next", response_model=List[FreeGameResponse])
def get_next_games(db: Session = Depends(get_db)):
    repo = GameRepository(db)
    return repo.get_upcoming_games()

@router.post("/games/refresh", dependencies=[Depends(verify_admin_access)])
def refresh_games():
    games = fetch_and_store_games()
    return {
        "message": "游戏数据已刷新",
        "current_count": len(games["current"]),
        "upcoming_count": len(games["upcoming"])
    }
