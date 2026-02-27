from typing import Dict, Any
from services.notification.wechat.pusher import WeChatOfficialPusher
from services.notification.qq.pusher import QQPusher

class PushService:
    def __init__(self):
        self.wechat_official_pusher = WeChatOfficialPusher()
        self.qq_pusher = QQPusher()
    
    def _format_current_game_message(self, game: Dict[str, Any]) -> str:
        return f"""Epic 本周免费游戏上线啦！
游戏名：{game.get('title', '未知')}
图片：{game.get('thumbnail', '无')}
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
        if contact_type == "wechat_official":
            return self.wechat_official_pusher.send_message(contact_id, message)
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
                    lines.append(f"   图片：{game.get('thumbnail', '无')}")
                    lines.append(f"   链接：{game.get('url', '无')}")
                    lines.append(f"   时间：{game.get('start_date', '未知')} ~ {game.get('end_date', '未知')}")
                    lines.append("")
                lines.append('请回复"确认"表示已收到，或回复"领取"表示已领取游戏。')
                message = "\n".join(lines)
        
        return self.push_to_user(contact_type, contact_id, message)


push_service = PushService()
