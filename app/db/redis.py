import redis
import json
from typing import List, Dict, Any, Optional
from app.core.config import get_settings
from app.core.logger import logger


class RedisClient:
    """Redis 客户端封装"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """延迟初始化 Redis 客户端"""
        if self._client is None:
            settings = get_settings()
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        return self._client

    def _get_key(self, key: str) -> str:
        """生成带前缀的 key"""
        settings = get_settings()
        return f"{settings.REDIS_PREFIX}:{key}"

    def set_current_week_games(self, games: List[Dict[str, Any]]) -> bool:
        """存储本周免费游戏"""
        try:
            settings = get_settings()
            key = self._get_key("games:current")
            self._get_client().setex(key, settings.REDIS_TTL, json.dumps(games))
            logger.info(f"已存储本周游戏: {len(games)} 款")
            return True
        except Exception as e:
            logger.error(f"存储本周游戏失败: {e}")
            return False

    def get_current_week_games(self) -> List[Dict[str, Any]]:
        """获取本周免费游戏"""
        try:
            key = self._get_key("games:current")
            data = self._get_client().get(key)
            if data:
                return json.loads(data)
            return []
        except Exception as e:
            logger.error(f"获取本周游戏失败: {e}")
            return []

    def set_next_week_games(self, games: List[Dict[str, Any]]) -> bool:
        """存储下周预告游戏"""
        try:
            settings = get_settings()
            key = self._get_key("games:upcoming")
            self._get_client().setex(key, settings.REDIS_TTL, json.dumps(games))
            logger.info(f"已存储下周预告: {len(games)} 款")
            return True
        except Exception as e:
            logger.error(f"存储下周预告失败: {e}")
            return False

    def get_next_week_games(self) -> List[Dict[str, Any]]:
        """获取下周预告游戏"""
        try:
            key = self._get_key("games:upcoming")
            data = self._get_client().get(key)
            if data:
                return json.loads(data)
            return []
        except Exception as e:
            logger.error(f"获取下周预告失败: {e}")
            return []

    def set_access_token(self, token: str, expires_in: int = 7200) -> bool:
        """存储微信 access_token"""
        try:
            key = self._get_key("wechat:access_token")
            self._get_client().setex(key, expires_in - 300, token)  # 提前5分钟过期
            return True
        except Exception as e:
            logger.error(f"存储 access_token 失败: {e}")
            return False

    def get_access_token(self) -> Optional[str]:
        """获取微信 access_token"""
        try:
            key = self._get_key("wechat:access_token")
            return self._get_client().get(key)
        except Exception as e:
            logger.error(f"获取 access_token 失败: {e}")
            return None

    def set_jsapi_ticket(self, ticket: str, expires_in: int = 7200) -> bool:
        """存储微信 jsapi_ticket"""
        try:
            key = self._get_key("wechat:jsapi_ticket")
            self._get_client().setex(key, expires_in - 300, ticket)
            return True
        except Exception as e:
            logger.error(f"存储 jsapi_ticket 失败: {e}")
            return False

    def get_jsapi_ticket(self) -> Optional[str]:
        """获取微信 jsapi_ticket"""
        try:
            key = self._get_key("wechat:jsapi_ticket")
            return self._get_client().get(key)
        except Exception as e:
            logger.error(f"获取 jsapi_ticket 失败: {e}")
            return None

    def health_check(self) -> bool:
        """检查 Redis 连接状态"""
        try:
            return self._get_client().ping()
        except Exception as e:
            logger.error(f"Redis 健康检查失败: {e}")
            return False


# 全局 Redis 客户端实例
redis_client = RedisClient()
