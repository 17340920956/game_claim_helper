from pydantic_settings import BaseSettings

class WechatOfficialSettings(BaseSettings):
    """
    微信公众号配置 (服务号)
    """
    # 微信公众号 AppID
    WECHAT_OFFICIAL_APPID: str = ""
    
    # 微信公众号 AppSecret
    WECHAT_OFFICIAL_SECRET: str = ""
    
    # 微信公众号 Token (用于服务器验证)
    WECHAT_OFFICIAL_TOKEN: str = ""
    
    # 微信公众号 EncodingAESKey (用于消息加密)
    WECHAT_OFFICIAL_AES_KEY: str = ""
    
    # 消息模板 ID (可选)
    WECHAT_OFFICIAL_TEMPLATE_ID: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"
