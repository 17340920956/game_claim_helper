import json
import redis
from typing import List, Dict, Optional, Any
from config import get_settings

settings = get_settings()


class RedisClient:
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    def _serialize_game(self, game: Dict[str, Any]) -> str:
        return json.dumps(game, ensure_ascii=False)
    
    def _deserialize_game(self, game_str: str) -> Dict[str, Any]:
        return json.loads(game_str)
    
    def set_current_week_games(self, games: List[Dict[str, Any]]) -> bool:
        key = "free_games:current_week"
        self.client.delete(key)
        for game in games:
            self.client.rpush(key, self._serialize_game(game))
        return True
    
    def get_current_week_games(self) -> List[Dict[str, Any]]:
        key = "free_games:current_week"
        games = self.client.lrange(key, 0, -1)
        return [self._deserialize_game(game) for game in games]
    
    def set_next_week_games(self, games: List[Dict[str, Any]]) -> bool:
        key = "free_games:next_week"
        self.client.delete(key)
        for game in games:
            self.client.rpush(key, self._serialize_game(game))
        return True
    
    def get_next_week_games(self) -> List[Dict[str, Any]]:
        key = "free_games:next_week"
        games = self.client.lrange(key, 0, -1)
        return [self._deserialize_game(game) for game in games]
    
    def add_notified_user(
        self, 
        game_slug: str, 
        user_id: int, 
        is_next_week: bool = False
    ) -> bool:
        prefix = "next_week" if is_next_week else "current_week"
        key = f"notified_users:{prefix}:{game_slug}"
        self.client.sadd(key, str(user_id))
        return True
    
    def is_user_notified(
        self, 
        game_slug: str, 
        user_id: int, 
        is_next_week: bool = False
    ) -> bool:
        prefix = "next_week" if is_next_week else "current_week"
        key = f"notified_users:{prefix}:{game_slug}"
        return self.client.sismember(key, str(user_id))
    
    def get_notified_users(
        self, 
        game_slug: str, 
        is_next_week: bool = False
    ) -> List[int]:
        prefix = "next_week" if is_next_week else "current_week"
        key = f"notified_users:{prefix}:{game_slug}"
        users = self.client.smembers(key)
        return [int(u) for u in users]
    
    def update_user_status(
        self, 
        game_slug: str, 
        user_id: int, 
        status: str,
        is_next_week: bool = False
    ) -> bool:
        prefix = "next_week" if is_next_week else "current_week"
        key = f"user_status:{prefix}:{game_slug}"
        self.client.hset(key, str(user_id), status)
        return True
    
    def get_user_status(
        self, 
        game_slug: str, 
        user_id: int,
        is_next_week: bool = False
    ) -> Optional[str]:
        prefix = "next_week" if is_next_week else "current_week"
        key = f"user_status:{prefix}:{game_slug}"
        return self.client.hget(key, str(user_id))
    
    def clear_week_data(self, is_next_week: bool = False) -> bool:
        prefix = "next_week" if is_next_week else "current_week"
        game_key = f"free_games:{prefix}"
        self.client.delete(game_key)
        
        keys = self.client.keys(f"notified_users:{prefix}:*")
        if keys:
            self.client.delete(*keys)
        
        keys = self.client.keys(f"user_status:{prefix}:*")
        if keys:
            self.client.delete(*keys)
        
        return True


redis_client = RedisClient()
