from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.services.game.scraper_service import fetch_and_store_games
from app.services.game.claim_service import epic_claim_service
from app.db.redis import redis_client
from app.schemas.game import GameResponse, GameListResponse
from app.core.security import verify_admin_access
from app.core.logger import logger
from datetime import datetime

router = APIRouter()


def _build_game_response(game_dict: dict) -> GameResponse:
    """将 Redis 中的游戏字典转换为响应模型"""
    return GameResponse(
        name=game_dict.get('name', '未知'),
        link=game_dict.get('link'),
        image_url=game_dict.get('image_url'),
        start_time=game_dict.get('start_time'),
        end_time=game_dict.get('end_time'),
        offer_id=game_dict.get('offer_id'),
        namespace=game_dict.get('namespace'),
        note=game_dict.get('note')
    )


@router.get("/games/current", response_model=GameListResponse)
async def get_current_free_games():
    """获取当前免费游戏列表"""
    try:
        games = redis_client.get_current_week_games()
        return GameListResponse(
            total=len(games),
            games=[_build_game_response(g) for g in games]
        )
    except Exception as e:
        logger.error(f"获取当前免费游戏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games/upcoming", response_model=GameListResponse)
async def get_upcoming_free_games():
    """获取即将免费游戏列表"""
    try:
        games = redis_client.get_next_week_games()
        return GameListResponse(
            total=len(games),
            games=[_build_game_response(g) for g in games]
        )
    except Exception as e:
        logger.error(f"获取即将免费游戏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games/all", response_model=GameListResponse)
async def get_all_free_games(
    status: Optional[str] = Query(None, description="游戏状态筛选: current, upcoming")
):
    """获取所有游戏列表（支持状态筛选）"""
    try:
        if status == "upcoming":
            games = redis_client.get_next_week_games()
        else:
            # 默认返回当前游戏
            games = redis_client.get_current_week_games()
        
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
