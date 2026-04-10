from typing import Dict, Any, List, Optional
from wechatpy.session.redisstorage import RedisStorage
from app.services.notification.base_pusher import BasePusher
from app.db.redis import redis_client
from app.clients.wechat.wechat_api_client import CustomWeChatClient
from app.core.config import get_settings
from app.core.logger import logger
from datetime import datetime

settings = get_settings()


def _local_time(dt) -> str:
    """UTC 转本地时间字符串"""
    if dt is None:
        return "未知"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except:
            return dt
    try:
        if dt.tzinfo:
            local_dt = dt.astimezone()
        else:
            local_dt = dt
        return local_dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(dt)

class WeChatOfficialPusher(BasePusher):
    def __init__(self):
        self.app_id = settings.WECHAT_OFFICIAL_APPID
        self.secret = settings.WECHAT_OFFICIAL_SECRET
        self.client = None
        if self.app_id and self.secret:
            try:
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
        发送文本消息（客服消息）
        注意：需要用户在 48 小时内与公众号互动过
        """
        if not self.client:
            return {"success": False, "error": "Client not initialized"}
        
        try:
            self.client.message.send_text(contact_id, message)
            logger.info(f"Message sent to {contact_id}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {"success": False, "error": str(e)}

    def send_game_notification(
        self, 
        contact_id: str, 
        game: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        发送游戏通知（使用文本消息）
        """
        message = f"""Epic 本周免费游戏上线啦！

游戏名称：{game.get('name', '未知')}
游戏图片：{game.get('image_url') or '暂无'}
领取链接：{game.get('link') or '暂无'}
开始时间：{_local_time(game.get('start_time'))}
结束时间：{_local_time(game.get('end_time'))}

请点击链接领取游戏，或回复"领取"让我们帮您领取。"""
        
        return self.send_message(contact_id, message)

    def send_games_batch_notification(
        self,
        contact_id: str,
        games: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量发送游戏通知（多款游戏）
        """
        if len(games) == 1:
            return self.send_game_notification(contact_id, games[0])
        
        lines = ["Epic 本周多款免费游戏上线！\n"]
        for i, game in enumerate(games, 1):
            lines.append(f"{i}. {game.get('name', '未知')}")
            lines.append(f"   图片：{game.get('image_url') or '暂无'}")
            lines.append(f"   链接：{game.get('link') or '暂无'}")
            lines.append(f"   时间：{_local_time(game.get('start_time'))} ~ {_local_time(game.get('end_time'))}")
            lines.append("")
        
        lines.append('请点击链接领取游戏，或回复"领取"让我们帮您领取。')
        message = "\n".join(lines)
        
        return self.send_message(contact_id, message)

    def send_image_message(
        self, 
        contact_id: str, 
        media_id: str
    ) -> Dict[str, Any]:
        """
        发送图片消息（客服消息）
        """
        if not self.client:
            return {"success": False, "error": "Client not initialized"}
        
        try:
            self.client.message.send_image(contact_id, media_id)
            logger.info(f"Image sent to {contact_id}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to send image: {e}")
            return {"success": False, "error": str(e)}

    def send_news_message(
        self, 
        contact_id: str, 
        articles: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        发送图文消息（客服消息）
        articles 格式：
        [
            {
                "title": "标题",
                "description": "描述",
                "url": "链接",
                "image": "图片链接"
            }
        ]
        """
        if not self.client:
            return {"success": False, "error": "Client not initialized"}
        
        try:
            self.client.message.send_articles(contact_id, articles)
            logger.info(f"News sent to {contact_id}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to send news: {e}")
            return {"success": False, "error": str(e)}

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
