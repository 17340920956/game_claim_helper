from functools import lru_cache
from .database import DatabaseSettings
from .epic import EpicSettings
from .wechat import WechatOfficialSettings
from .qq import QQSettings
from .app import AppSettings

class Settings(DatabaseSettings, EpicSettings, WechatOfficialSettings, QQSettings, AppSettings):
    """
    全局配置聚合类
    继承所有子配置类，提供统一的访问入口
    """
    pass

@lru_cache()
def get_settings() -> Settings:
    """
    获取全局配置单例
    使用 lru_cache 缓存配置对象，避免重复读取 .env 文件
    """
    return Settings()
