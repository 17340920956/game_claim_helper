import requests
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from config import get_settings

settings = get_settings()


class BasePusher(ABC):
    @abstractmethod
    def send_message(self, contact_id: str, message: str) -> Dict[str, Any]:
        pass


class WeChatPusher(BasePusher):
    def __init__(self):
        self.corp_id = settings.WECHAT_CORP_ID
        self.agent_id = settings.WECHAT_AGENT_ID
        self.secret = settings.WECHAT_SECRET
        self._access_token = None
    
    def _get_access_token(self) -> Optional[str]:
        if not self.corp_id or not self.secret:
            return None
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.secret
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data.get("errcode") == 0:
                return data.get("access_token")
        except Exception as e:
            print(f"获取微信access_token失败: {e}")
        
        return None
    
    def send_message(self, contact_id: str, message: str) -> Dict[str, Any]:
        if not self.corp_id or not self.agent_id or not self.secret:
            return {
                "success": False,
                "error": "微信配置不完整"
            }
        
        access_token = self._get_access_token()
        if not access_token:
            return {
                "success": False,
                "error": "获取access_token失败"
            }
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        data = {
            "touser": contact_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": message
            },
            "safe": 0
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("errcode") == 0:
                return {"success": True, "msg_id": result.get("msgid")}
            else:
                return {
                    "success": False,
                    "error": result.get("errmsg", "发送失败")
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


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


class PushService:
    def __init__(self):
        self.wechat_pusher = WeChatPusher()
        self.qq_pusher = QQPusher()
    
    def _format_current_game_message(self, game: Dict[str, Any]) -> str:
        return f"""Epic 本周免费游戏上线啦！
游戏名：{game.get('title', '未知')}
领取链接：{game.get('url', '无')}
开始时间：{game.get('start_date', '未知')}
结束时间：{game.get('end_date', '未知')}

请回复"确认"表示已收到，或回复"领取"表示已领取游戏。"""
    
    def _format_next_week_message(self, games: list) -> str:
        titles = [g.get('title', '未知') for g in games]
        title_list = "\n".join([f"  - {t}" for t in titles])
        
        return f"""下周 Epic 免费游戏预告：
{title_list}

敬请期待！请回复"确认"表示已收到消息。"""
    
    def push_to_user(
        self, 
        contact_type: str, 
        contact_id: str, 
        message: str
    ) -> Dict[str, Any]:
        if contact_type == "wechat":
            return self.wechat_pusher.send_message(contact_id, message)
        elif contact_type == "qq":
            return self.qq_pusher.send_message(contact_id, message)
        else:
            return {"success": False, "error": f"不支持的联系方式: {contact_type}"}
    
    def push_game_notification(
        self,
        contact_type: str,
        contact_id: str,
        game: Dict[str, Any],
        is_next_week: bool = False
    ) -> Dict[str, Any]:
        if is_next_week:
            message = self._format_next_week_message([game])
        else:
            message = self._format_current_game_message(game)
        
        return self.push_to_user(contact_type, contact_id, message)
    
    def push_games_batch(
        self,
        contact_type: str,
        contact_id: str,
        games: list,
        is_next_week: bool = False
    ) -> Dict[str, Any]:
        if is_next_week:
            message = self._format_next_week_message(games)
        else:
            if len(games) == 1:
                message = self._format_current_game_message(games[0])
            else:
                lines = ["Epic 本周多款免费游戏上线！\n"]
                for i, game in enumerate(games, 1):
                    lines.append(f"{i}. {game.get('title', '未知')}")
                    lines.append(f"   链接：{game.get('url', '无')}")
                    lines.append(f"   时间：{game.get('start_date', '未知')} ~ {game.get('end_date', '未知')}")
                    lines.append("")
                lines.append("请回复"确认"表示已收到，或回复"领取"表示已领取游戏。")
                message = "\n".join(lines)
        
        return self.push_to_user(contact_type, contact_id, message)


push_service = PushService()
