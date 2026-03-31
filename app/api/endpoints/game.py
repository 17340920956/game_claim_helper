from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.repositories.game.game_repository import GameRepository
from app.services.game.scraper_service import fetch_and_store_games
from app.services.game.claim_service import epic_claim_service
from app.schemas.game import GameResponse, GameListResponse
from app.core.security import verify_admin_access
from app.core.logger import logger
from datetime import datetime

router = APIRouter()


def _build_game_response(game) -> GameResponse:
    return GameResponse.model_validate(game)


@router.get("/games/current", response_model=GameListResponse)
async def get_current_free_games(db: Session = Depends(get_db)):
    """获取当前免费游戏列表"""
    try:
        repo = GameRepository(db)
        games = repo.get_active_games()
        return GameListResponse(
            total=len(games),
            games=[_build_game_response(g) for g in games]
        )
    except Exception as e:
        logger.error(f"获取当前免费游戏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games/upcoming", response_model=GameListResponse)
async def get_upcoming_free_games(db: Session = Depends(get_db)):
    """获取即将免费游戏列表"""
    try:
        repo = GameRepository(db)
        games = repo.get_upcoming_games()
        return GameListResponse(
            total=len(games),
            games=[_build_game_response(g) for g in games]
        )
    except Exception as e:
        logger.error(f"获取即将免费游戏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games/all", response_model=GameListResponse)
async def get_all_free_games(
    status: Optional[str] = Query(None, description="游戏状态筛选: current, upcoming, expired"),
    db: Session = Depends(get_db)
):
    """获取所有游戏列表（支持状态筛选）"""
    try:
        repo = GameRepository(db)
        status_map = {
            "current": repo.get_active_games,
            "upcoming": repo.get_upcoming_games,
            "expired": repo.get_expired_games,
        }
        games = status_map.get(status, repo.get_all_games)()
        return GameListResponse(
            total=len(games),
            games=[_build_game_response(g) for g in games]
        )
    except Exception as e:
        logger.error(f"获取游戏列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/games/refresh", dependencies=[Depends(verify_admin_access)])
async def refresh_free_games():
    """手动刷新游戏数据（立即爬取最新游戏），需要管理员权限"""
    try:
        logger.info("手动触发游戏数据刷新")
        games = fetch_and_store_games()
        return {
            "success": True,
            "message": "游戏数据刷新成功",
            "data": {
                "current_count": len(games["current"]),
                "upcoming_count": len(games["upcoming"]),
                "refreshed_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"刷新游戏数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game_by_id(game_id: int, db: Session = Depends(get_db)):
    """根据 ID 获取游戏详情"""
    try:
        repo = GameRepository(db)
        game = repo.get_by_id(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="游戏不存在")
        return _build_game_response(game)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取游戏详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
