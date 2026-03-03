from typing import Dict, Any, List, Optional
from wechatpy.session.redisstorage import RedisStorage
from app.services.notification.base_pusher import BasePusher
from app.db.redis import redis_client
from app.clients.wechat.wechat_api_client import CustomWeChatClient
from app.core.config import get_settings
from app.core.logger import logger

settings = get_settings()

class WeChatOfficialPusher(BasePusher):
    def __init__(self):
        self.app_id = settings.WECHAT_OFFICIAL_APPID
        self.secret = settings.WECHAT_OFFICIAL_SECRET
        self.client = None
        if self.app_id and self.secret:
            try:
                # Use Redis for access token storage
                session_interface = RedisStorage(
                    redis_client.client,
                    prefix="wechatpy"
                )
                self.client = CustomWeChatClient(
                    self.app_id, 
                    self.secret, 
                    session=session_interface
                )
            except Exception as e:
                logger.error(f"WeChatClient init failed: {e}")

    def send_message(self, contact_id: str, message: str) -> Dict[str, Any]:
        """
        Dummy implementation for abstract method
        """
        return {"success": False, "error": "WeChat message pushing is disabled."}

    def check_callback(self) -> Dict[str, Any]:
        """
        Check callback configuration
        """
        if not self.client:
            return {"success": False, "error": "Client not initialized"}
        try:
            res = self.client.misc.callback_check()
            return {"success": True, "data": res}
        except Exception as e:
            return {"success": False, "error": str(e)}
