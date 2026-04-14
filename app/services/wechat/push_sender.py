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
        发送游戏通知（使用图文消息）
        """
        try:
            # 使用图文消息发送，包含图片、标题、描述和链接
            articles = [{
                "title": f"🎮 {game.get('name', '未知游戏')}",
                "description": f"免费时间：\n{_local_time(game.get('start_time'))} 至 {_local_time(game.get('end_time'))}\n\n点击查看游戏详情",
                "url": game.get('link') or 'https://store.epicgames.com/zh-CN/free-games',
                "image": game.get('image_url') or 'https://via.placeholder.com/800x400?text=Free+Game'
            }]
            
            result = self.send_news_message(contact_id, articles)
            
            # 如果图文消息发送失败，降级为文本消息
            if not result.get("success"):
                logger.warning(f"Failed to send news message, fallback to text: {result.get('error')}")
                message = f"""Epic 本周免费游戏上线啦！

游戏名称：{game.get('name', '未知')}
游戏图片：{game.get('image_url') or '暂无'}
游戏链接：{game.get('link') or '暂无'}
开始时间：{_local_time(game.get('start_time'))}
结束时间：{_local_time(game.get('end_time'))}

请访问 Epic 官网查看游戏。"""
                return self.send_message(contact_id, message)
            
            return result
        except Exception as e:
            logger.error(f"Failed to send game notification: {e}")
            return {"success": False, "error": str(e)}

    def send_games_batch_notification(
        self,
        contact_id: str,
        games: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量发送游戏通知（多款游戏） - 修改为逐个推送
        """
        results = []
        for game in games:
            result = self.send_game_notification(contact_id, game)
            results.append(result)
        
        # 返回最后一个推送结果
        return results[-1] if results else {"success": False, "error": "No games to push"}

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
