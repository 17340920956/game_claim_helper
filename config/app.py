from pydantic_settings import BaseSettings

class AppSettings(BaseSettings):
    """
    应用基础配置
    """
    # 调度器时区 (默认上海)
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"

    class Config:
        env_file = ".env"
        extra = "ignore"
