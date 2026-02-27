import requests
from typing import Dict, Any
from config import get_settings
from services.notification.base import BasePusher

settings = get_settings()

class QQPusher(BasePusher):
    def __init__(self):
        self.api_url = settings.QQ_BOT_API_URL
        self.token = settings.QQ_BOT_TOKEN
    
    def send_message(self, contact_id: str, message: str) -> Dict[str, Any]:
        if not self.api_url:
            return {
                "success": False,
                "error": "QQ机器人API未配置"
            }
        
        url = f"{self.api_url}/send_private_msg"
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        data = {
            "user_id": contact_id,
            "message": message
        }
        
        try:
            response = requests.post(
                url, 
                json=data, 
                headers=headers,
                timeout=10
            )
            result = response.json()
            
            if result.get("status") == "ok":
                return {"success": True, "data": result.get("data")}
            else:
                return {
                    "success": False,
                    "error": result.get("status", "发送失败")
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
