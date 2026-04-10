from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class GameResponse(BaseModel):
    """游戏响应模型"""
    name: str
    link: Optional[str] = None
    image_url: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    offer_id: Optional[str] = None
    namespace: Optional[str] = None
    note: Optional[str] = None

class GameListResponse(BaseModel):
    """游戏列表响应模型"""
    total: int
    games: list[GameResponse]
