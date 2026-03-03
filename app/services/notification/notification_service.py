from typing import Dict, Any, Optional, List
from app.services.wechat.push_sender import WeChatOfficialPusher
from app.core.security import create_confirmation_token
from app.core.config import get_settings
from app.models.base import User, FreeGame

settings = get_settings()

class PushService:
    """
    推送服务编排层
    负责格式化消息内容，并根据用户联系方式选择合适的推送渠道（微信）
    """
    def __init__(self):
        self.wechat_official_pusher = WeChatOfficialPusher()
    
    def _format_current_game_message(self, game: FreeGame, user_id: Optional[int] = None) -> str:
        """
        格式化本周免费游戏消息
        """
        msg = f"""Epic 本周免费游戏上线啦！
游戏名：{game.name}
图片：{game.image_url or '无'}
领取链接：{game.link or '无'}
开始时间：{game.start_time}
结束时间：{game.end_time}"""

        # Token logic removed as per schema simplification (PushLog no longer has confirmation_status)
        # But if we still want confirmation link, we can keep it. 
        # Since the user asked to optimize based on schema, and schema removed confirmation_status,
        # I will remove the confirmation link logic for now to stay strict, 
        # or keep it if it doesn't conflict. 
        # The schema kept 'note' in PushLog.
        
        msg += '\n\n请回复"确认"表示已收到，或回复"领取"表示已领取游戏。'
        return msg
    
    def _format_next_week_message(self, games: List[FreeGame]) -> str:
        """
        格式化下周预告消息
        """
        titles = [g.name for g in games]
        title_list = "\n".join([f"  - {t}" for t in titles])
        
        return f"""下周 Epic 免费游戏预告：
{title_list}

敬请期待！请回复"确认"表示已收到消息。"""
    
    def push_to_user(
        self, 
        user: User, 
        message: str
    ) -> Dict[str, Any]:
        """
        底层推送接口：根据用户绑定的方式推送
        优先使用微信
        """
        if user.wx_id:
            return self.wechat_official_pusher.send_message(user.wx_id, message)
        # elif user.qq_id:
        #     return self.qq_pusher.send_message(user.qq_id, message)
        else:
            return {"success": False, "error": "用户未绑定有效的联系方式"}
    
    def push_game_notification(
        self,
        user: User,
        game: FreeGame,
        is_next_week: bool = False
    ) -> Dict[str, Any]:
        """
        推送单个游戏的通知
        """
        if is_next_week:
            message = self._format_next_week_message([game])
        else:
            message = self._format_current_game_message(game, user.id)
        
        return self.push_to_user(user, message)
    
    def push_games_batch(
        self,
        user: User,
        games: List[FreeGame],
        is_next_week: bool = False
    ) -> Dict[str, Any]:
        """
        批量推送游戏通知
        """
        if is_next_week:
            message = self._format_next_week_message(games)
        else:
            if len(games) == 1:
                message = self._format_current_game_message(games[0], user.id)
            else:
                lines = ["Epic 本周多款免费游戏上线！\n"]
                for i, game in enumerate(games, 1):
                    lines.append(f"{i}. {game.name}")
                    lines.append(f"   图片：{game.image_url or '无'}")
                    lines.append(f"   链接：{game.link or '无'}")
                    lines.append(f"   时间：{game.start_time} ~ {game.end_time}")
                    lines.append("")
                lines.append('请回复"确认"表示已收到，或回复"领取"表示已领取游戏。')
                message = "\n".join(lines)
        
        return self.push_to_user(user, message)


push_service = PushService()
