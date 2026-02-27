from pydantic_settings import BaseSettings

class EpicSettings(BaseSettings):
    """
    Epic 游戏平台相关配置
    """
    # Epic 免费游戏页面 URL
    EPIC_FREE_GAMES_URL: str = "https://store.epicgames.com/en-US/free-games"

    class Config:
        env_file = ".env"
        extra = "ignore"
