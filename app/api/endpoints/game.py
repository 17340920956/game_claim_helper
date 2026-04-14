"""
游戏查询API模块

提供Epic免费游戏的查询接口，包括：
- 当前免费游戏列表
- 即将免费游戏预告
- 游戏数据刷新
- 游戏展示网页

数据存储：Redis
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime

from app.services.game.scraper_service import fetch_and_store_games
from app.db.redis import redis_client
from app.schemas.game import GameResponse, GameListResponse
from app.core.logger import logger

# 路由实例
router = APIRouter()

# 模板引擎（用于渲染网页）
templates = Jinja2Templates(directory="app/templates")


def _build_game_response(game_dict: dict) -> GameResponse:
    """
    将Redis中的游戏字典转换为响应模型
    
    参数：
        game_dict: 从Redis获取的游戏数据字典
    
    返回：
        GameResponse: 标准化的游戏响应对象
    """
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


def _format_time(time_str: Optional[str]) -> Optional[str]:
    """
    格式化ISO时间字符串为中文显示格式
    
    参数：
        time_str: ISO格式时间字符串（如：2024-01-15T16:00:00.000Z）
    
    返回：
        str: 格式化后的时间（如：01月15日 16:00）
        None: 输入为空时返回None
    """
    if not time_str:
        return None
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return dt.strftime('%m月%d日 %H:%M')
    except:
        return time_str


@router.get("/games/current", response_model=GameListResponse)
async def get_current_free_games():
    """
    获取当前免费游戏列表
    
    从Redis获取本周正在免费的游戏列表
    
    返回：
        GameListResponse: 包含游戏总数和游戏详情列表
    
    异常：
        500: Redis连接错误或数据解析错误
    """
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
    """
    获取即将免费游戏列表
    
    从Redis获取下周预告的免费游戏列表
    
    返回：
        GameListResponse: 包含游戏总数和游戏详情列表
    
    异常：
        500: Redis连接错误或数据解析错误
    """
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
    status: Optional[str] = Query(None, description="游戏状态筛选: current-当前, upcoming-即将")
):
    """
    获取所有游戏列表（支持状态筛选）
    
    参数：
        status: 筛选条件
            - current: 仅返回当前免费游戏
            - upcoming: 仅返回即将免费游戏
            - None: 返回当前免费游戏（默认）
    
    返回：
        GameListResponse: 包含游戏总数和游戏详情列表
    
    异常：
        500: Redis连接错误或数据解析错误
    """
    try:
        games = redis_client.get_next_week_games() if status == "upcoming" else redis_client.get_current_week_games()
        return GameListResponse(
            total=len(games),
            games=[_build_game_response(g) for g in games]
        )
    except Exception as e:
        logger.error(f"获取游戏列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/games/refresh")
async def refresh_free_games():
    """
    手动刷新游戏数据
    
    立即触发游戏数据爬取，从Epic官网获取最新免费游戏信息
    
    返回：
        dict: 包含刷新结果
            - success: 是否成功
            - message: 提示信息
            - data: 详细数据（当前游戏数、预告游戏数、刷新时间）
    
    异常：
        500: 爬取或存储过程中发生错误
    """
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
    游戏展示网页
    
    渲染一个美观的网页展示当前和即将免费的游戏
    用于微信推送中的链接跳转
    
    参数：
        request: FastAPI请求对象（模板渲染需要）
    
    返回：
        HTML页面: 包含游戏列表、图片、时间信息的网页
    
    异常：
        500: 渲染过程中发生错误
    """
    try:
        current_games = redis_client.get_current_week_games()
        upcoming_games = redis_client.get_next_week_games()

        # 格式化时间显示
        for game in current_games:
            game['end_time'] = _format_time(game.get('end_time'))

        for game in upcoming_games:
            game['start_time'] = _format_time(game.get('start_time'))

        return templates.TemplateResponse("games.html", {
            "request": request,
            "current_games": current_games,
            "upcoming_games": upcoming_games,
            "update_time": datetime.now().strftime('%Y年%m月%d日 %H:%M')
        })
    except Exception as e:
        logger.error(f"渲染游戏展示页面失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
