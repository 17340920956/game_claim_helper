from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.services.game.scraper_service import fetch_and_store_games
from app.db.redis import redis_client
from app.schemas.game import GameResponse, GameListResponse
from app.core.security import verify_admin_access
from app.core.logger import logger
from datetime import datetime

router = APIRouter()

# 设置模板目录
templates = Jinja2Templates(directory="app/templates")


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


@router.post("/games/refresh")
async def refresh_free_games():
    """手动刷新游戏数据（立即爬取最新游戏）"""
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


@router.get("/games/view")
async def games_view_page(request: Request):
    """
    游戏展示网页 - 聚合本周免费游戏和下周预告
    用于微信推送时展示游戏图片和详细信息
    """
    try:
        # 从 Redis 获取游戏数据
        current_games = redis_client.get_current_week_games()
        upcoming_games = redis_client.get_next_week_games()
        
        # 格式化时间显示
        def format_time(time_str):
            if not time_str:
                return None
            try:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return dt.strftime('%m月%d日 %H:%M')
            except:
                return time_str
        
        # 处理游戏数据
        for game in current_games:
            game['end_time'] = format_time(game.get('end_time'))
        
        for game in upcoming_games:
            game['start_time'] = format_time(game.get('start_time'))
        
        return templates.TemplateResponse("games.html", {
            "request": request,
            "current_games": current_games,
            "upcoming_games": upcoming_games,
            "update_time": datetime.now().strftime('%Y年%m月%d日 %H:%M')
        })
    except Exception as e:
        logger.error(f"渲染游戏展示页面失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
