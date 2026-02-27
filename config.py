from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://admin:Yang1024%40q@localhost:3306/game_claim_helper"
    REDIS_URL: str = "redis://admin:ecommerce_pwd@localhost:6379/0"
    EPIC_FREE_GAMES_URL: str = "https://store.epicgames.com/en-US/free-games"
    
    WECHAT_CORP_ID: str = ""
    WECHAT_AGENT_ID: str = ""
    WECHAT_SECRET: str = ""
    
    QQ_BOT_API_URL: str = ""
    QQ_BOT_TOKEN: str = ""
    
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
