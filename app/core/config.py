from pydantic_settings import BaseSettings
import os


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


def _parse_redis_password(redis_url: str) -> str:
    """从 REDIS_URL 解析密码
    
    格式: redis://:password@host:port/db
    密码中可能包含 @ 字符，需要正确处理
    """
    if not redis_url:
        return ""
    
    try:
        # 移除协议前缀
        if '://' in redis_url:
            redis_url = redis_url.split('://', 1)[1]
        
        # 格式: :password@host:port/db
        # 找到最后一个 @ 符号，它后面是 host:port/db
        if '@' not in redis_url:
            return ""
        
        # 从后往前找 @，因为密码中可能有 @
        at_index = redis_url.rfind('@')
        if at_index == -1:
            return ""
        
        # @ 前面的部分是 :password
        auth_part = redis_url[:at_index]
        
        # 移除开头的 :
        if auth_part.startswith(':'):
            password = auth_part[1:]
        else:
            password = auth_part
        
        return password
        
    except Exception:
        pass
    return ""


# 全局设置实例
_settings = None

def get_settings() -> Settings:
    global _settings
    
    # 每次都创建新的实例，确保环境变量被重新读取
    settings = Settings()
    
    # 从 REDIS_URL 解析密码（如果 REDIS_PASSWORD 为空）
    if not settings.REDIS_PASSWORD and settings.REDIS_URL:
        settings.REDIS_PASSWORD = _parse_redis_password(settings.REDIS_URL)
    
    _settings = settings
    return settings
