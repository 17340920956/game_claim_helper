from pydantic_settings import BaseSettings

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

from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    return Settings()
