from typing import Dict, Any, Optional, List
from app.services.wechat.push_sender import WeChatOfficialPusher
from app.core.config import get_settings
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


class PushService:
    """
    推送服务编排层
    负责格式化消息内容，并根据用户联系方式选择合适的推送渠道（微信）
    使用客服消息接口（个人订阅号可用）
    """
    def __init__(self):
        self.wechat_official_pusher = WeChatOfficialPusher()

    def _format_current_game_message(self, game: Dict[str, Any]) -> str:
        """格式化本周免费游戏消息"""
        msg = f"""Epic 本周免费游戏上线啦！

游戏名：{game.get('name', '未知')}
图片：{game.get('image_url') or '暂无'}
领取链接：{game.get('link') or '暂无'}
开始时间：{_local_time(game.get('start_time'))}
结束时间：{_local_time(game.get('end_time'))}

请访问 Epic 官网手动领取游戏。"""
        return msg

    def _format_next_week_message(self, games: List[Dict[str, Any]]) -> str:
        """格式化下周预告消息"""
        titles = [g.get('name', '未知') for g in games]
        title_list = "\n".join([f"  - {t}" for t in titles])
        return f"""下周 Epic 免费游戏预告：
{title_list}

敬请期待！"""

    def push_to_openid(self, openid: str, message: str) -> Dict[str, Any]:
        """底层推送接口：根据openid推送"""
        return self.wechat_official_pusher.send_message(openid, message)

    def push_game_notification(
        self, openid: str, game: Dict[str, Any], is_next_week: bool = False
    ) -> Dict[str, Any]:
        """推送单个游戏的通知"""
        if is_next_week:
            message = self._format_next_week_message([game])
            return self.push_to_openid(openid, message)
        else:
            return self.wechat_official_pusher.send_game_notification(openid, game)

    def push_games_batch(
        self, openid: str, games: List[Dict[str, Any]], is_next_week: bool = False
    ) -> Dict[str, Any]:
        """批量推送游戏通知"""
        if is_next_week:
            message = self._format_next_week_message(games)
            return self.push_to_openid(openid, message)
        else:
            return self.wechat_official_pusher.send_games_batch_notification(openid, games)


push_service = PushService()
