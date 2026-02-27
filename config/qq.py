from pydantic_settings import BaseSettings

class QQSettings(BaseSettings):
    """
    QQ 机器人配置 (基于 OneBot/CQHttp)
    """
    # QQ 机器人 API 地址 (例如: http://localhost:3000)
    QQ_BOT_API_URL: str = ""
    
    # QQ 机器人访问令牌 (可选)
    QQ_BOT_TOKEN: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"
