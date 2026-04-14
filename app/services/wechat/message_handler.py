from app.db.redis import redis_client
from wechatpy import create_reply
from wechatpy.messages import BaseMessage
from wechatpy.replies import ArticlesReply
from app.core.logger import logger
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
import json


# Asia/Shanghai UTC+8
_SHANGHAI_TZ_OFFSET = datetime.now().astimezone().utcoffset() or __import__('datetime').timedelta(hours=8)

# 被动图文：无封面时使用；描述过长时截断（微信约 512 字节量级，保守按字符截断）
DEFAULT_GAME_COVER_URL = "https://via.placeholder.com/800x400?text=Epic+Free"
EPIC_FREE_STORE_ZH = "https://store.epicgames.com/zh-CN/free-games"
WECHAT_ARTICLE_DESC_MAX = 500
WECHAT_ARTICLE_TITLE_MAX = 64
MAX_PASSIVE_ARTICLES = 10


def _format_time(dt) -> str:
    """将 UTC datetime 转为本地时间字符串显示"""
    if dt is None:
        return "未知"
    try:
        if dt.tzinfo is not None:
            local_dt = dt.astimezone()
        else:
            local_dt = dt
        return local_dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(dt)


class WeChatService:
    def __init__(self):
        pass

    # ==================== 游戏数据管理 ====================

    def _get_active_games(self) -> List[Dict[str, Any]]:
        """从Redis获取当前免费游戏（正在免费期内）"""
        games = redis_client.get_current_week_games()
        active_games = []
        now = datetime.now(timezone.utc)
        
        for game in games:
            start_time_str = game.get("start_time")
            end_time_str = game.get("end_time")
            
            if start_time_str and end_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                    
                    if start_time <= now <= end_time:
                        active_games.append(game)
                except Exception as e:
                    logger.warning(f"解析游戏时间失败: {e}")
                    continue
        
        return active_games
    
    def _get_upcoming_games(self) -> List[Dict[str, Any]]:
        """从Redis获取即将免费游戏"""
        games = redis_client.get_next_week_games()
        upcoming_games = []
        now = datetime.now(timezone.utc)
        
        for game in games:
            start_time_str = game.get("start_time")
            
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    
                    if start_time > now:
                        upcoming_games.append(game)
                except Exception as e:
                    logger.warning(f"解析游戏时间失败: {e}")
                    continue
        
        return upcoming_games

    # ==================== 消息处理主流程 ====================

    def process_message(self, msg: BaseMessage, openid: str) -> Union[str, Dict[str, Any]]:
        """处理微信消息并返回回复内容"""
        reply_content = "收到"

        if msg.type == 'text':
            content = msg.content.strip()
            logger.info(f"Received message from {openid}: {content}")
            reply_content = self._handle_text_message(openid, content)

        elif msg.type == 'event':
            if msg.event == 'subscribe':
                logger.info(f"User subscribed: {openid}")
                reply_content = "感谢关注！\n\n回复'帮助'查看可用命令。"

        return reply_content

    def process_message_for_multi_reply(self, msg: BaseMessage, openid: str) -> Dict[str, Any]:
        """
        处理消息并返回多回复内容（用于客服消息推送模式）
        返回格式：{"type": "multi_reply", "messages": [msg1, msg2, ...], "articles": [article1, article2, ...]}
        """
        result = {"type": "multi_reply", "messages": [], "articles": []}
        
        if msg.type == 'text':
            content = msg.content.strip()
            logger.info(f"Received message from {openid}: {content} (multi-reply mode)")
            
            # 处理游戏查询 - 返回多条图文
            if content.lower() in ('游戏', '免费游戏', '查看游戏', '查看免费游戏', '当前游戏'):
                games = self._get_active_games()
                upcoming_games = self._get_upcoming_games()
                
                logger.info(f"多消息模式: 当前免费={len(games)}, 即将免费={len(upcoming_games)}")
                
                if not games and not upcoming_games:
                    result["messages"].append("当前没有免费游戏信息。\n\n回复'刷新'更新游戏数据。")
                    return result
                
                # 为每款当前免费游戏生成独立的图文消息
                for i, game in enumerate(games):
                    article = self._game_passive_article(game, upcoming=False)
                    result["articles"].append(article)
                    logger.info(f"  添加游戏图文 {i+1}: {game.get('name')}")
                
                # 为每款即将免费的游戏生成独立的图文消息
                for i, game in enumerate(upcoming_games):
                    article = self._game_passive_article(game, upcoming=True)
                    result["articles"].append(article)
                    logger.info(f"  添加即将免费图文 {i+1}: {game.get('name')}")
                
                # 添加汇总文本消息
                summary_lines = [f"📊 本周共找到 {len(games)} 款正在免费的游戏"]
                if upcoming_games:
                    summary_lines.append(f"以及 {len(upcoming_games)} 款即将免费的游戏")
                summary_lines.append("\n已为您逐条展示，请向上滑动查看全部内容！")
                result["messages"].append("\n".join(summary_lines))
                
                return result
            
            # 其他命令使用原有逻辑，但包装为 multi_reply 格式
            reply = self._handle_text_message(openid, content)
            if isinstance(reply, dict) and reply.get("type") == "articles":
                result["articles"] = reply.get("articles", [])
            else:
                result["messages"].append(reply if isinstance(reply, str) else str(reply))
            
            return result
        
        elif msg.type == 'event':
            if msg.event == 'subscribe':
                result["messages"].append("感谢关注！\n\n回复'帮助'查看可用命令。")
        
        return result

    def _handle_text_message(self, openid: str, content: str) -> Union[str, Dict[str, Any]]:
        """处理文本消息"""

        content_lower = content.lower()
        
        # 命令映射
        if content_lower in ('帮助', 'help', '?'):
            return self._get_help_message()
        elif content_lower in ('游戏', '免费游戏', '查看游戏', '查看免费游戏', '当前游戏'):
            return self._get_current_games_message()
        elif content_lower in ('下周游戏', '即将免费'):
            return self._get_upcoming_games_message()
        elif content_lower in ('刷新', '刷新游戏'):
            return self._handle_refresh_games()
        return "收到您的消息！\n\n回复'帮助'查看可用命令。"

    # ==================== 游戏查询 ====================

    def _game_time_info_active(self, game: Dict[str, Any]) -> str:
        start_time_str = game.get("start_time")
        end_time_str = game.get("end_time")
        if not start_time_str or not end_time_str:
            return ""
        try:
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            return f"\n免费时间：{_format_time(start_time)} ~ {_format_time(end_time)}"
        except Exception:
            return ""

    def _game_time_info_upcoming(self, game: Dict[str, Any]) -> str:
        start_time_str = game.get("start_time")
        if not start_time_str:
            return ""
        try:
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            return f"\n开始免费：{_format_time(start_time)}"
        except Exception:
            return ""

    def _get_current_games_message(self) -> str:
        """获取当前免费游戏信息"""
        games = self._get_active_games()
        
        if not games:
            return "当前没有正在免费的游戏。\n\n回复'刷新'更新游戏数据。"
        
        lines = [f"🎮 本周免费游戏（共 {len(games)} 款）\n"]
        
        for i, game in enumerate(games, 1):
            name = game.get("name", "未知游戏")
            desc = game.get("description", "")
            link = game.get("link", EPIC_FREE_STORE_ZH)
            
            # 截断描述
            if len(desc) > 100:
                desc = desc[:97] + "..."
            
            lines.append(f"{i}. {name}")
            lines.append(f"   {desc}")
            lines.append(f"   链接：{link}")
            lines.append(self._game_time_info_active(game))
            lines.append("")
        
        lines.append("回复'下周游戏'查看即将免费的游戏")
        return "\n".join(lines)

    def _get_upcoming_games_message(self) -> str:
        """获取即将免费游戏信息"""
        games = self._get_upcoming_games()
        
        if not games:
            return "暂无即将免费的游戏信息。\n\n回复'刷新'更新游戏数据。"
        
        lines = [f"📅 即将免费游戏（共 {len(games)} 款）\n"]
        
        for i, game in enumerate(games, 1):
            name = game.get("name", "未知游戏")
            desc = game.get("description", "")
            link = game.get("link", EPIC_FREE_STORE_ZH)
            
            if len(desc) > 100:
                desc = desc[:97] + "..."
            
            lines.append(f"{i}. {name}")
            lines.append(f"   {desc}")
            lines.append(f"   链接：{link}")
            lines.append(self._game_time_info_upcoming(game))
            lines.append("")
        
        return "\n".join(lines)

    def _game_passive_article(self, game: Dict[str, Any], upcoming: bool = False) -> Dict[str, str]:
        """为被动图文回复生成单条图文"""
        name = game.get("name", "未知游戏")
        description = game.get("description", "")
        cover = game.get("cover") or DEFAULT_GAME_COVER_URL
        link = game.get("link") or EPIC_FREE_STORE_ZH
        
        # 截断描述
        if len(description) > WECHAT_ARTICLE_DESC_MAX:
            description = description[:WECHAT_ARTICLE_DESC_MAX-3] + "..."
        
        # 添加时间信息
        if upcoming:
            time_info = self._game_time_info_upcoming(game)
            title_prefix = "📅 即将免费"
        else:
            time_info = self._game_time_info_active(game)
            title_prefix = "🎮 本周免费"
        
        # 截断标题
        title = f"{title_prefix}：{name}"
        if len(title) > WECHAT_ARTICLE_TITLE_MAX:
            title = title[:WECHAT_ARTICLE_TITLE_MAX-3] + "..."
        
        full_description = f"{description}{time_info}"
        
        return {
            "title": title,
            "description": full_description,
            "picurl": cover,
            "url": link,
        }

    def _handle_refresh_games(self) -> str:
        """处理刷新游戏请求"""
        from app.services.game.epic_games import epic_service
        
        try:
            epic_service.fetch_and_cache_games()
            return "游戏数据刷新成功！\n\n回复'游戏'查看最新免费游戏。"
        except Exception as e:
            logger.error(f"刷新游戏失败: {e}")
            return f"刷新游戏失败：{str(e)}\n\n请稍后再试。"

    def _get_help_message(self) -> str:
        """获取帮助信息"""
        return (
            "🎮 Epic 免费游戏查询助手\n\n"
            "可用命令：\n"
            "• 游戏 / 免费游戏 - 查看本周免费游戏\n"
            "• 下周游戏 / 即将免费 - 查看即将免费的游戏\n"
            "• 刷新 / 刷新游戏 - 刷新游戏数据\n"
            "• 帮助 - 显示此帮助信息\n\n"
            "提示：游戏数据每天自动更新"
        )

    def generate_xml_response(self, reply_content, msg, openid: str = None) -> str:
        """生成微信 XML 响应"""
        from wechatpy.replies import TextReply, ArticlesReply
        
        if isinstance(reply_content, dict) and reply_content.get("type") == "articles":
            # 图文消息
            articles = reply_content.get("articles", [])
            if articles:
                reply = ArticlesReply(message=msg)
                for article in articles:
                    reply.add_article({
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "image": article.get("picurl", ""),
                        "url": article.get("url", "")
                    })
                return reply.render()
        
        # 文本消息
        if isinstance(reply_content, str):
            reply = TextReply(message=msg, content=reply_content)
            return reply.render()
        
        # 默认返回
        reply = TextReply(message=msg, content="收到")
        return reply.render()
