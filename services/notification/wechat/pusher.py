from typing import Dict, Any
from wechatpy import WeChatClient
from wechatpy.exceptions import WeChatClientException
from config import get_settings
from services.notification.base import BasePusher

settings = get_settings()

class WeChatOfficialPusher(BasePusher):
    def __init__(self):
        self.app_id = settings.WECHAT_OFFICIAL_APPID
        self.secret = settings.WECHAT_OFFICIAL_SECRET
        self.client = None
        if self.app_id and self.secret:
            try:
                self.client = WeChatClient(self.app_id, self.secret)
            except Exception as e:
                print(f"WeChatClient init failed: {e}")

    def send_message(self, contact_id: str, message: str) -> Dict[str, Any]:
        if not self.client:
            return {"success": False, "error": "微信公众号配置不完整"}
        
        try:
            # 尝试发送客服消息（需用户48小时内有互动）
            # 如果配置了模板ID，这里应该优先使用模板消息，但目前简化处理
            res = self.client.message.send_text(contact_id, message)
            return {"success": True, "data": res}
        except WeChatClientException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}
