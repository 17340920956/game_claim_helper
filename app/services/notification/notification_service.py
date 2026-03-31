from typing import Dict, Any, Optional, List
from app.services.wechat.push_sender import WeChatOfficialPusher
from app.core.config import get_settings
from app.models.base import User, FreeGame

settings = get_settings()


def _local_time(dt) -> str:
    """UTC 转本地时间字符串"""
    if dt is None:
        return "未知"
    try:
        if dt.tzinfo:
            local_dt = dt.astimezone()
        else:
            local_dt = dt
        return local_dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(dt)


class PushService:
    """
    推送服务编排层
    负责格式化消息内容，并根据用户联系方式选择合适的推送渠道（微信）
    使用客服消息接口（个人订阅号可用）
    """
    def __init__(self):
        self.wechat_official_pusher = WeChatOfficialPusher()

    def _format_current_game_message(self, game: FreeGame, user_id: Optional[int] = None) -> str:
        """格式化本周免费游戏消息"""
        msg = f"""Epic 本周免费游戏上线啦！

游戏名：{game.name}
图片：{game.image_url or '暂无'}
领取链接：{game.link or '暂无'}
开始时间：{_local_time(game.start_time)}
结束时间：{_local_time(game.end_time)}

请回复"确认"表示已收到，或回复"领取"让我们帮您领取游戏。"""
        return msg

    def _format_next_week_message(self, games: List[FreeGame]) -> str:
        """格式化下周预告消息"""
        titles = [g.name for g in games]
        title_list = "\n".join([f"  - {t}" for t in titles])
        return f"""下周 Epic 免费游戏预告：
{title_list}

敬请期待！请回复"确认"表示已收到消息。"""

    def push_to_user(self, user: User, message: str) -> Dict[str, Any]:
        """底层推送接口：根据用户绑定的方式推送"""
        if user.wx_id:
            return self.wechat_official_pusher.send_message(user.wx_id, message)
        else:
            return {"success": False, "error": "用户未绑定微信"}

    def push_game_notification(
        self, user: User, game: FreeGame, is_next_week: bool = False
    ) -> Dict[str, Any]:
        """推送单个游戏的通知"""
        if is_next_week:
            message = self._format_next_week_message([game])
            return self.push_to_user(user, message)
        else:
            if user.wx_id:
                return self.wechat_official_pusher.send_game_notification(user.wx_id, game)
            else:
                return {"success": False, "error": "用户未绑定微信"}

    def push_games_batch(
        self, user: User, games: List[FreeGame], is_next_week: bool = False
    ) -> Dict[str, Any]:
        """批量推送游戏通知"""
        if is_next_week:
            message = self._format_next_week_message(games)
            return self.push_to_user(user, message)
        else:
            if user.wx_id:
                return self.wechat_official_pusher.send_games_batch_notification(user.wx_id, games)
            else:
                return {"success": False, "error": "用户未绑定微信"}

    def push_news_notification(
        self, user: User, articles: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """推送图文消息"""
        if user.wx_id:
            return self.wechat_official_pusher.send_news_message(user.wx_id, articles)
        else:
            return {"success": False, "error": "用户未绑定微信"}


push_service = PushService()
