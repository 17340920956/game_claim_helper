from pydantic_settings import BaseSettings
from functools import lru_cache


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 从 REDIS_URL 解析密码
        if not self.REDIS_PASSWORD and self.REDIS_URL:
            self.REDIS_PASSWORD = self._parse_redis_password(self.REDIS_URL)
    
    @staticmethod
    def _parse_redis_password(redis_url: str) -> str:
        """从 REDIS_URL 解析密码"""
        if not redis_url or '@' not in redis_url:
            return ""
        try:
            # redis://:password@host:port/db
            # 提取 @ 之前的部分
            auth_part = redis_url.split('@')[0]
            # 查找最后一个 : 后面的内容作为密码
            if ':@' in auth_part:
                # 格式: redis://:password@host
                password = auth_part.split(':@')[-1]
                return password
            elif '://:' in auth_part:
                # 格式: redis://:password
                password = auth_part.split('://:')[-1]
                return password
        except Exception:
            pass
        return ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()
