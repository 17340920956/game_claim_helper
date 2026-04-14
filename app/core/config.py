from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    """
    全局配置聚合类
    """
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_PREFIX: str = "game_claim"
    REDIS_TTL: int = 604800  # 7天
    
    # 兼容旧配置：从 REDIS_URL 解析
    REDIS_URL: str = ""

    # Epic
    EPIC_FREE_GAMES_URL: str = "https://store.epicgames.com/en-US/free-games"

    # WeChat Official
    WECHAT_OFFICIAL_APPID: str = ""
    WECHAT_OFFICIAL_SECRET: str = ""
    WECHAT_OFFICIAL_TOKEN: str = ""
    WECHAT_OFFICIAL_AES_KEY: str = ""
    WECHAT_OFFICIAL_TEMPLATE_ID: str = ""
    WECHAT_OFFICIAL_URL: str = "http://localhost:8000"
    WECHAT_OFFICIAL_STABLE_TOKEN_URL: str = "https://api.weixin.qq.com/cgi-bin/stable_token"
    WECHAT_OFFICIAL_CALLBACK_CHECK_URL: str = "https://api.weixin.qq.com/cgi-bin/callback/check"
    
    # App
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @field_validator('REDIS_PASSWORD', mode='before')
    @classmethod
    def parse_redis_url(cls, v, info):
        """从 REDIS_URL 解析密码"""
        if v:
            return v
        redis_url = info.data.get('REDIS_URL', '')
        if redis_url and '@' in redis_url:
            # redis://:password@host:port/db
            try:
                # 提取密码部分
                auth_part = redis_url.split('@')[0]
                if ':@' in auth_part:
                    password = auth_part.split(':@')[-1]
                    return password
            except:
                pass
        return v

from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    return Settings()
