from sqlalchemy.orm import Session
from app.repositories.wechat.wechat_repository import WeChatRepository
from app.repositories.game.game_repository import GameRepository
from app.repositories.notification.push_log_repository import PushLogRepository
from app.services.game.claim_service import epic_claim_service
from wechatpy import create_reply
from wechatpy.messages import BaseMessage
from app.core.logger import logger
from app.models.base import FreeGame
from app.schemas.base import PushLogCreate
from typing import Optional
from datetime import datetime, timezone


# Asia/Shanghai UTC+8
_SHANGHAI_TZ_OFFSET = datetime.now().astimezone().utcoffset() or __import__('datetime').timedelta(hours=8)


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
    def __init__(self, db: Session):
        self.repository = WeChatRepository(db)
        self.game_repo = GameRepository(db)
        self.log_repo = PushLogRepository(db)
        self.user_state = {}

    def process_message(self, msg: BaseMessage, openid: str) -> str:
        """处理微信消息并返回回复内容"""
        reply_content = "收到"
        user = self.repository.get_user_by_openid(openid)

        if not user:
            user = self.repository.create_user(openid)
            logger.info(f"New WeChat user created: {openid}")
            reply_content = "欢迎关注！您的账号已自动创建。\n\n回复'帮助'查看可用命令。"
        else:
            if user.is_del:
                self.repository.update_user_active_status(user, True)
                reply_content = "欢迎回来！\n\n回复'帮助'查看可用命令。"

        if msg.type == 'text':
            content = msg.content.strip().lower()
            logger.info(f"Received message from {openid}: {content}")
            reply_content = self._handle_text_message(user.id, openid, content, user)

        elif msg.type == 'event':
            if msg.event == 'subscribe':
                logger.info(f"User subscribed: {openid}")
                reply_content = "感谢关注！\n\n回复'帮助'查看可用命令。"
            elif msg.event == 'unsubscribe':
                logger.info(f"User unsubscribed: {openid}")
                if user:
                    self.repository.update_user_active_status(user, False)
                return "success"

        return reply_content

    def _handle_text_message(self, user_id: int, openid: str, content: str, user) -> str:
        """处理文本消息"""

        # 检查用户状态（多轮对话）
        state = self.user_state.get(user_id)
        if state:
            return self._handle_state_message(user_id, openid, content, user, state)

        # 命令映射
        commands = {
            frozenset(['帮助', 'help', '?']): self._get_help_message,
            frozenset(['确认', '收到']): lambda: "收到确认，感谢您的回复！",
            frozenset(['领取', '领取游戏']): lambda: self._handle_claim_request(user),
            frozenset(['绑定', '绑定账号']): None,  # 特殊处理
            frozenset(['解绑', '解绑账号']): lambda: self._handle_unbind(user),
            frozenset(['游戏', '免费游戏', '查看游戏', '查看免费游戏', '当前游戏']): self._get_current_games_message,
            frozenset(['下周游戏', '即将免费']): self._get_upcoming_games_message,
            frozenset(['状态', '我的状态']): lambda: self._get_user_status(user),
            frozenset(['刷新', '刷新游戏']): self._handle_refresh_games,
        }

        for cmd_set, handler in commands.items():
            if content in cmd_set:
                if content in ('绑定', '绑定账号'):
                    self.user_state[user_id] = {'step': 'bind_email'}
                    return "请输入您的 Epic 账号邮箱："
                return handler() if handler else "收到"

        return "收到您的消息！\n\n回复'帮助'查看可用命令。"

    def _handle_state_message(self, user_id: int, openid: str, content: str, user, state: dict) -> str:
        """处理多轮对话状态"""
        step = state.get('step')

        if step == 'bind_email':
            # 验证邮箱格式
            if '@' not in content or '.' not in content:
                return "邮箱格式不正确，请重新输入："
            self.user_state[user_id] = {'step': 'bind_password', 'email': content}
            return f"邮箱：{content}\n\n请输入您的 Epic 账号密码："

        elif step == 'bind_password':
            email = state.get('email')
            password = content

            if not password or len(password) < 3:
                return "密码不能为空且至少3位，请重新输入："

            # 保存到数据库（密码会自动加密）
            self.repository.update_user_epic_account(user, email, password)
            del self.user_state[user_id]

            return f"Epic 账号绑定成功！\n邮箱：{email}\n\n回复'领取'让我们帮您领取免费游戏。"

        elif step == 'confirm_claim':
            if content in ('确认', '是', 'yes', 'y'):
                game = state.get('game')
                if not game:
                    del self.user_state[user_id]
                    return "游戏信息已过期，请重新查看免费游戏。"

                result = self._do_claim(user, game)
                del self.user_state[user_id]
                return result
            else:
                del self.user_state[user_id]
                return "已取消领取。"

        else:
            if user_id in self.user_state:
                del self.user_state[user_id]
            return "操作已取消。回复'帮助'查看可用命令。"

    def _handle_claim_request(self, user) -> str:
        """处理领取请求"""
        if not user.epic_email or not user.epic_password:
            return "您还未绑定 Epic 账号。\n\n回复'绑定'开始绑定流程。"

        games = self.game_repo.get_active_games()
        if not games:
            return "当前没有免费游戏可领取。"

        game_list = "\n".join([f"  {i+1}. {g.name}" for i, g in enumerate(games)])
        return f"当前免费游戏：\n{game_list}\n\n回复\"确认\"开始自动领取所有游戏。"

    def _do_claim(self, user, game: FreeGame) -> str:
        """执行实际领取操作"""
        if not game.offer_id or not game.namespace:
            return f"游戏「{game.name}」缺少领取信息(offer_id/namespace)，请手动到 Epic 商店领取。\n{game.link or ''}"

        try:
            result = epic_claim_service.claim_game(
                email=user.epic_email,
                encrypted_password=user.epic_password,
                offer_id=game.offer_id,
                namespace=game.namespace,
            )

            if result["success"]:
                msg = f"领取「{game.name}」成功！{result.get('message', '')}"
                logger.info(f"用户 {user.id} 领取游戏 {game.name} 成功")
            else:
                msg = f"领取「{game.name}」失败：{result.get('message', '未知错误')}"
                logger.warning(f"用户 {user.id} 领取游戏 {game.name} 失败: {msg}")

            return msg
        except Exception as e:
            logger.exception(f"领取游戏异常: {e}")
            return f"领取「{game.name}」时发生系统异常，请稍后再试。"

    def _handle_unbind(self, user) -> str:
        """处理解绑请求"""
        if not user.epic_email:
            return "您还未绑定 Epic 账号。"
        self.repository.update_user_epic_account(user, None, None)
        return "Epic 账号已解绑。"

    def _get_current_games_message(self) -> str:
        """获取当前免费游戏消息"""
        games = self.game_repo.get_active_games()
        if not games:
            return "当前没有免费游戏。\n\n回复'下周游戏'查看即将免费的游戏。"

        lines = ["🎮 当前免费游戏：\n"]
        for i, game in enumerate(games, 1):
            lines.append(f"{i}. {game.name}")
            if game.link:
                lines.append(f"   链接：{game.link}")
            if game.start_time and game.end_time:
                lines.append(f"   时间：{_format_time(game.start_time)} ~ {_format_time(game.end_time)}")
            lines.append("")

        lines.append("💡 回复'领取'让我们帮您领取游戏。")
        lines.append("💡 回复'下周游戏'查看即将免费的游戏。")
        return "\n".join(lines)

    def _get_upcoming_games_message(self) -> str:
        """获取即将免费游戏消息"""
        games = self.game_repo.get_upcoming_games()
        if not games:
            return "暂无即将免费的游戏信息。"

        lines = ["🎮 即将免费游戏：\n"]
        for i, game in enumerate(games, 1):
            lines.append(f"{i}. {game.name}")
            if game.link:
                lines.append(f"   链接：{game.link}")
            if game.start_time:
                lines.append(f"   开始时间：{_format_time(game.start_time)}")
            lines.append("")

        lines.append("💡 敬请期待！")
        return "\n".join(lines)

    def _handle_refresh_games(self) -> str:
        """处理刷新游戏请求"""
        try:
            from app.services.game.scraper_service import fetch_and_store_games
            games = fetch_and_store_games()
            current_count = len(games["current"])
            upcoming_count = len(games["upcoming"])
            return f"✅ 游戏数据刷新成功！\n\n当前免费: {current_count} 款\n即将免费: {upcoming_count} 款\n\n回复'游戏'查看详情。"
        except Exception as e:
            logger.error(f"刷新游戏失败: {e}")
            return "❌ 刷新失败，请稍后再试。"

    def _get_user_status(self, user) -> str:
        """获取用户状态"""
        lines = ["📊 您的账号状态：\n"]
        lines.append(f"微信 ID：{user.wx_id}")
        lines.append(f"Epic 邮箱：{user.epic_email or '未绑定'}")
        lines.append(f"账号状态：{'正常' if not user.is_del else '已注销'}")
        return "\n".join(lines)

    def _get_help_message(self) -> str:
        """获取帮助消息"""
        return """📖 可用命令：

🎮 游戏相关：
• 游戏 - 查看当前免费游戏
• 下周游戏 - 查看即将免费游戏
• 刷新 - 刷新游戏数据

🎁 领取相关：
• 领取 - 自动领取免费游戏（需先绑定）
• 绑定 - 绑定 Epic 账号
• 解绑 - 解绑 Epic 账号

ℹ️ 其他：
• 状态 - 查看账号状态
• 帮助 - 查看此帮助信息

💡 每周五我们会自动推送 Epic 免费游戏通知给您。"""

    def generate_xml_response(self, reply_content: str, msg: BaseMessage) -> str:
        if reply_content == "success":
            return "success"
        reply = create_reply(reply_content, msg)
        return reply.render()
