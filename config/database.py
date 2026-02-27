from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    """
    数据库配置
    """
    # 数据库连接 URL
    # 格式: mysql+pymysql://user:password@host:port/database
    DATABASE_URL: str = "mysql+pymysql://admin:Yang1024%40q@localhost:3306/game_claim_helper"
    
    # Redis 连接 URL
    # 格式: redis://user:password@host:port/db
    REDIS_URL: str = "redis://admin:ecommerce_pwd@localhost:6379/0"

    class Config:
        env_file = ".env"
        extra = "ignore"
