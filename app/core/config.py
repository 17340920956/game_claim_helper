
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    全局配置聚合类
    """
    # Database
    DATABASE_URL: str = "mysql+pymysql://gch:Gch1024!@42.194.176.11:3306/game_claim_helper"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Epic
    EPIC_FREE_GAMES_URL: str = "https://store.epicgames.com/en-US/free-games"

    # WeChat Official
    WECHAT_OFFICIAL_APPID: str = ""
    WECHAT_OFFICIAL_SECRET: str = ""
    WECHAT_OFFICIAL_TOKEN: str = ""
    WECHAT_OFFICIAL_AES_KEY: str = ""
    WECHAT_OFFICIAL_TEMPLATE_ID: str = ""
    # WeChat Official API URLs
    # 稳定版凭证接口
    WECHAT_OFFICIAL_STABLE_TOKEN_URL: str = "https://api.weixin.qq.com/cgi-bin/stable_token"
    # 网络检测接口
    WECHAT_OFFICIAL_CALLBACK_CHECK_URL: str = "https://api.weixin.qq.com/cgi-bin/callback/check"
    
    # App
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"

    # Security
    SECRET_KEY: str = "change-me-to-a-secure-secret-key"
    ADMIN_API_KEY: str = "admin-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"

from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    return Settings()
