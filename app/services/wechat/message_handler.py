from sqlalchemy.orm import Session
from app.repositories.wechat.wechat_repository import WeChatRepository
from app.repositories.notification.push_log_repository import PushLogRepository
from app.services.game.claim_service import epic_claim_service
from app.db.redis import redis_client
from wechatpy import create_reply
from wechatpy.messages import BaseMessage
from wechatpy.replies import ArticlesReply
from app.core.logger import logger
from app.schemas.base import PushLogCreate
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
import json
import threading


# Asia/Shanghai UTC+8
_SHANGHAI_TZ_OFFSET = datetime.now().astimezone().utcoffset() or __import__('datetime').timedelta(hours=8)

# Redis 中多轮对话状态的 key 前缀和过期时间
USER_STATE_PREFIX = "wechat:user_state:"
USER_STATE_TTL = 600  # 10分钟过期

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
    def __init__(self, db: Session):
        self.repository = WeChatRepository(db)
        self.log_repo = PushLogRepository(db)

    # ==================== Redis 状态管理 ====================

    def _get_state(self, user_id: int) -> Optional[dict]:
        """从 Redis 获取用户多轮对话状态"""
        key = f"{USER_STATE_PREFIX}{user_id}"
        data = redis_client.client.get(key)
        if data:
            try:
                return json.loads(data)
            except Exception:
                return None
        return None

    def _set_state(self, user_id: int, state: dict):
        """保存用户多轮对话状态到 Redis"""
        key = f"{USER_STATE_PREFIX}{user_id}"
        redis_client.client.set(key, json.dumps(state, ensure_ascii=False), ex=USER_STATE_TTL)

    def _clear_state(self, user_id: int):
        """清除用户多轮对话状态"""
        key = f"{USER_STATE_PREFIX}{user_id}"
        redis_client.client.delete(key)

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
            content = msg.content.strip()
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

    def process_message_for_multi_reply(self, msg: BaseMessage, openid: str) -> Dict[str, Any]:
        """
        处理消息并返回多回复内容（用于客服消息推送模式）
        返回格式：{"type": "multi_reply", "messages": [msg1, msg2, ...], "articles": [article1, article2, ...]}
        """
        result = {"type": "multi_reply", "messages": [], "articles": []}
        
        user = self.repository.get_user_by_openid(openid)
        if not user:
            user = self.repository.create_user(openid)
            logger.info(f"New WeChat user created: {openid}")
            result["messages"].append("欢迎关注！您的账号已自动创建。\n\n回复'帮助'查看可用命令。")
            return result
        
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
                summary_lines.append("\n回复「领取」可自动领取免费游戏")
                result["messages"].append("\n".join(summary_lines))
                
                return result
            
            # 其他命令使用原有逻辑，但包装为 multi_reply 格式
            reply = self._handle_text_message(user.id, openid, content, user)
            if isinstance(reply, dict) and reply.get("type") == "articles":
                result["articles"] = reply.get("articles", [])
            else:
                result["messages"].append(reply if isinstance(reply, str) else str(reply))
            
            return result
        
        elif msg.type == 'event':
            if msg.event == 'subscribe':
                result["messages"].append("感谢关注！\n\n回复'帮助'查看可用命令。")
            elif msg.event == 'unsubscribe':
                if user:
                    self.repository.update_user_active_status(user, False)
        
        return result

    def _handle_text_message(self, user_id: int, openid: str, content: str, user) -> Union[str, Dict[str, Any]]:
        """处理文本消息"""

        # 统一取消命令（任何状态下都能触发）
        if content.strip().lower() in ('取消', '退出', 'cancel', 'quit', 'q'):
            state = self._get_state(user_id)
            if state:
                self._clear_state(user_id)
                return "操作已取消。\n\n回复'帮助'查看可用命令。"

        # 绑定已由后台完成并清状态后，用户仍回复「完成」
        if content.strip() in ('完成', '好了'):
            fresh = self.repository.get_user_by_id(user_id)
            if fresh and self._user_has_epic_binding(fresh):
                return "绑定已生效。\n\n回复「领取」即可代领免费游戏。"

        # 优先检查用户多轮对话状态
        state = self._get_state(user_id)
        if state:
            return self._handle_state_message(user_id, openid, content, user, state)

        # 命令映射
        content_lower = content.lower()
        commands = {
            frozenset(['帮助', 'help', '?']): self._get_help_message,
            frozenset(['确认', '收到']): lambda: "收到确认，感谢您的回复！",
            frozenset(['领取', '领取游戏']): lambda: self._handle_claim_request(user, openid),
            frozenset(['绑定', '绑定账号']): None,  # 特殊处理
            frozenset(['解绑', '解绑账号']): lambda: self._handle_unbind(user),
            frozenset(['游戏', '免费游戏', '查看游戏', '查看免费游戏', '当前游戏']): lambda: self._get_current_games_message(),
            frozenset(['下周游戏', '即将免费']): lambda: self._get_upcoming_games_message(),
            frozenset(['状态', '我的状态']): lambda: self._get_user_status(user),
            frozenset(['刷新', '刷新游戏']): self._handle_refresh_games,
        }

        for cmd_set, handler in commands.items():
            if content_lower in cmd_set:
                if content_lower in ('绑定', '绑定账号'):
                    return self._handle_bind_request(user, openid)
                return handler() if handler else "收到"

        return "收到您的消息！\n\n回复'帮助'查看可用命令。"

    # ==================== 多轮对话处理 ====================

    def _handle_state_message(self, user_id: int, openid: str, content: str, user, state: dict) -> str:
        """处理多轮对话状态"""
        step = state.get('step')

        if step == 'waiting_device_auth':
            if content.strip().lower() in ('完成', '好了', 'ok', 'yes', '是'):
                # 后台线程可能已用掉 device_code 并完成写入，必须先读库避免重复 poll 失败
                fresh = self.repository.get_user_by_id(user_id)
                if fresh and self._user_has_epic_binding(fresh):
                    self._clear_state(user_id)
                    return "绑定已生效。\n\n回复「领取」即可代领免费游戏。"

                device_code = state.get('device_code')
                if device_code:
                    try:
                        auth_result = epic_claim_service.poll_device_code(device_code, timeout=20, interval=3)
                        access_token = auth_result["access_token"]
                        refresh_token = auth_result.get("refresh_token")
                        account_id = auth_result["account_id"]
                        email = self._get_epic_email(access_token, account_id)

                        device_auth = None
                        try:
                            device_auth = epic_claim_service.create_device_auth(access_token, account_id)
                        except Exception as e:
                            logger.warning(f"Failed to create Device Auth: {e}")

                        self._save_binding_to_db(user_id, account_id, email, refresh_token, device_auth)
                        self._clear_state(user_id)
                        bound = self.repository.get_user_by_id(user_id)
                        return self._bind_success_message(bound) if bound else self._bind_success_message(user)
                    except Exception as e:
                        logger.info(f"User claimed done but auth not ready: {e}")
                        return "⏳ 还未检测到授权成功，请确认已在浏览器中完成登录。\n\n稍后再回复「完成」，或回复「取消」退出。"
            return "⏳ 请先在浏览器中完成 Epic 账号授权。\n\n授权完成后回复「完成」；也可等待系统自动提示成功。回复「取消」退出绑定。"

        else:
            self._clear_state(user_id)
            return "操作已超时或无效。\n\n回复「帮助」查看可用命令。"

    # ==================== 绑定相关 ====================

    @staticmethod
    def _user_has_epic_binding(user) -> bool:
        if not user:
            return False
        return bool(user.epic_refresh_token or (user.epic_device_id and user.epic_device_secret))

    @staticmethod
    def _bind_success_message(user) -> str:
        return (
            f"✅ Epic 账号绑定成功！\n📧 邮箱：{user.epic_email or '已关联'}\n\n"
            f"回复「领取」让我们帮您领取免费游戏。"
        )

    def _handle_bind_request(self, user, openid: str) -> str:
        """处理绑定请求 - 使用 Device Code 流程"""
        if self._user_has_epic_binding(user):
            return (
                f"您已绑定 Epic 账号（{user.epic_email or '已关联'}）。\n\n"
                f"回复「解绑」可先解除绑定再重新绑定。"
            )

        return self._handle_bind_request_with_message(user, openid=openid)

    def _handle_bind_request_with_message(self, user, prefix_msg: str = "", openid: str = "") -> str:
        """处理绑定请求：下发浏览器授权链接，后台轮询成功后写库并发客服提示。"""
        try:
            device_code_data = epic_claim_service.create_device_code()
            verification_uri = device_code_data.get("verification_uri_complete", "")
            user_code = device_code_data.get("user_code", "")
            expires_in = int(device_code_data.get("expires_in") or 600)
            minutes = max(1, expires_in // 60)

            if not verification_uri:
                return "❌ 获取授权链接失败，请稍后再试。"

            self._set_state(user.id, {
                'step': 'waiting_device_auth',
                'device_code': device_code_data.get("device_code"),
                'user_code': user_code,
            })

            self._start_background_poll(
                user.id,
                device_code_data.get("device_code"),
                openid,
                expires_in=min(expires_in + 60, 720),
            )

            bind_message = (
                f"🔗 请在浏览器中打开以下链接完成 Epic 授权：\n\n"
                f"{verification_uri}\n\n"
                f"授权码：{user_code}\n\n"
                f"请在约 {minutes} 分钟内完成。授权成功后您将收到「绑定成功」提示；\n"
                f"也可在完成后回复「完成」。回复「取消」退出绑定。"
            )

            return prefix_msg + bind_message
        except Exception as e:
            logger.error(f"创建 Device Code 失败: {e}")
            return "❌ 获取授权链接失败，请稍后再试。"

    def _start_background_poll(self, user_id: int, device_code: str, openid: str, expires_in: int = 660):
        """后台轮询 Device Code；成功后写库、清除会话状态，并发一条客服文字提示（避免仅靠回复「完成」）。"""
        def poll():
            try:
                auth_result = epic_claim_service.poll_device_code(
                    device_code, timeout=max(60, expires_in), interval=10
                )
                access_token = auth_result["access_token"]
                refresh_token = auth_result.get("refresh_token")
                account_id = auth_result["account_id"]
                email = self._get_epic_email(access_token, account_id)

                device_auth = None
                try:
                    device_auth = epic_claim_service.create_device_auth(access_token, account_id)
                    logger.info(f"Background poll: Device Auth created for user {user_id}")
                except Exception as e:
                    logger.warning(f"Background poll: Failed to create Device Auth: {e}")

                self._save_binding_to_db(user_id, account_id, email, refresh_token, device_auth)
                self._clear_state(user_id)

                if openid:
                    try:
                        from app.services.wechat.push_sender import WeChatOfficialPusher
                        pusher = WeChatOfficialPusher()
                        msg = (
                            f"✅ Epic 账号绑定成功！\n📧 邮箱：{email or '已关联'}\n\n"
                            f"回复「领取」让我们帮您领取免费游戏。"
                        )
                        result = pusher.send_message(openid, msg)
                        if not result.get("success"):
                            logger.warning(f"Bind success customer msg failed: {result.get('error')}")
                    except Exception as e:
                        logger.warning(f"Bind success customer notify error: {e}")
            except Exception as e:
                logger.info(f"Background poll: User {user_id} device code wait ended: {e}")

        thread = threading.Thread(target=poll, daemon=True)
        thread.start()

    def _save_binding_to_db(self, user_id: int, account_id: str, email: str,
                             refresh_token: str = None, device_auth: dict = None):
        """保存 Epic 绑定信息到数据库"""
        from app.db.session import SessionLocal
        from app.models.base import User
        from app.core.crypto import encrypt_password

        db = SessionLocal()
        try:
            user_obj = db.query(User).filter(User.id == user_id).first()
            if user_obj:
                if account_id:
                    user_obj.epic_id = account_id
                if email:
                    user_obj.epic_email = email
                if refresh_token:
                    user_obj.epic_refresh_token = encrypt_password(refresh_token)
                if device_auth:
                    user_obj.epic_device_id = device_auth.get("device_id")
                    user_obj.epic_device_secret = encrypt_password(device_auth.get("secret", ""))
                db.commit()
                logger.info(f"User {user_id} Epic binding saved, email={email}")
        except Exception as e:
            logger.error(f"Failed to save Epic binding for user {user_id}: {e}")
            db.rollback()
        finally:
            db.close()

    def _get_epic_email(self, access_token: str, account_id: str = "") -> Optional[str]:
        """通过 access_token 获取用户邮箱和显示名称"""
        try:
            import requests
            if account_id:
                # 通过 accountId 获取详细信息（所有者可获取 email）
                resp = requests.get(
                    f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{account_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("email")
                    display_name = data.get("displayName")
                    # 优先返回 email，没有则返回 displayName
                    return email or display_name
        except Exception as e:
            logger.warning(f"获取 Epic 账号信息失败: {e}")
        return None

    # ==================== 领取相关 ====================

    def _handle_claim_request(self, user, openid: str = "") -> str:
        """处理领取请求 - 先尝试自动授权，失败时引导重新绑定"""
        # 检查认证方式
        has_refresh_token = bool(user.epic_refresh_token)
        has_device_auth = bool(user.epic_device_id and user.epic_device_secret)
        has_password = bool(user.epic_email and user.epic_password)

        logger.info(f"User {user.id} claim request: refresh_token={has_refresh_token}, "
                   f"device_auth={has_device_auth}, password={has_password}")

        if not has_refresh_token and not has_device_auth and not has_password:
            return "您还未绑定 Epic 账号。\n\n回复'绑定'开始绑定流程。"

        try:
            games = self._get_active_games()
            logger.info(f"Found {len(games)} active games")
        except Exception as e:
            logger.exception(f"Failed to get active games: {e}")
            return f"❌ 查询游戏失败：{str(e)}\n\n请稍后再试。"

        if not games:
            return "当前没有免费游戏可领取。\n\n回复'刷新'更新游戏数据。"

        # 尝试领取第一游戏以检查凭证有效性
        first_game = games[0]
        test_result = self._do_claim(user, first_game)
        
        # 检测到凭证失效，自动清除并引导重新绑定
        if "已失效" in test_result or "重新绑定" in test_result or "无可用认证" in test_result:
            logger.warning(f"User {user.id} credentials expired, auto-clearing and triggering rebind")
            
            # 清除失效的凭证
            self.repository.clear_user_epic_account(user)
            
            # 自动触发绑定流程
            return self._handle_bind_request_with_message(
                user,
                f"⚠️ 您的 Epic 授权已失效，已自动清除。\n\n"
                f"请重新绑定以继续领取游戏：\n\n",
                openid=openid,
            )

        # 第一游戏领取成功或非凭证问题，继续领取剩余游戏
        results = [test_result]
        for game in games[1:]:
            result = self._do_claim(user, game)
            results.append(result)

        return "\n\n".join(results) + "\n\n回复'游戏'查看更多。"

    def _do_claim(self, user, game: Dict[str, Any]) -> str:
        """执行实际领取操作"""
        game_name = game.get("name", "未知游戏")
        offer_id = game.get("offer_id")
        namespace = game.get("namespace")
        
        if not offer_id or not namespace:
            logger.warning(f"Game {game_name} missing offer_id or namespace")
            return f"游戏「{game_name}」缺少领取信息，请手动领取。\n{game.get('link', '')}"

        try:
            logger.info(f"Attempting to claim game {game_name} for user {user.id}, "
                       f"has_refresh_token={bool(user.epic_refresh_token)}, "
                       f"has_device_auth={bool(user.epic_device_id and user.epic_device_secret)}, "
                       f"account_id={user.epic_id}")
            
            result = epic_claim_service.claim_game(
                offer_id=offer_id,
                namespace=namespace,
                encrypted_refresh_token=user.epic_refresh_token,
                device_id=user.epic_device_id,
                encrypted_device_secret=user.epic_device_secret,
                account_id=user.epic_id,
                email=user.epic_email or "",
                encrypted_password=user.epic_password or "",
                game_url=game.get("note") or "",
            )

            logger.info(f"Claim result for {game_name}: success={result.get('success')}, "
                       f"message={result.get('message')}")

            # 如果领取成功且返回了新的 refresh_token，更新数据库
            if result.get("new_refresh_token"):
                try:
                    self.repository.update_user_refresh_token(user, result["new_refresh_token"])
                    logger.info(f"Updated refresh token for user {user.id}")
                except Exception as e:
                    logger.error(f"Failed to update refresh token for user {user.id}: {e}", exc_info=True)
                    # Session 已回滚，继续返回结果

            if result["success"]:
                msg = f"✅ 领取「{game_name}」成功！{result.get('message', '')}"
                logger.info(f"用户 {user.id} 领取游戏 {game_name} 成功")
            else:
                msg = f"❌ 领取「{game_name}」失败：{result.get('message', '未知错误')}"
                logger.warning(f"用户 {user.id} 领取游戏 {game_name} 失败: {msg}")

            return msg
        except Exception as e:
            logger.exception(f"领取游戏异常: {e}")
            # 确保回滚 Session 以避免影响后续操作
            try:
                self.repository.db.rollback()
            except Exception:
                pass
            return f"❌ 领取「{game_name}」时发生异常：{str(e)}"

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
        end_time_str = game.get("end_time")
        if not start_time_str:
            return ""
        try:
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            line = f"\n开始时间：{_format_time(start_time)}"
            if end_time_str:
                end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                line += f" ~ {_format_time(end_time)}"
            return line
        except Exception:
            return ""

    def _game_passive_article(self, game: Dict[str, Any], *, upcoming: bool) -> Dict[str, str]:
        """被动回复单条图文：封面图 + 可点击 Url + 描述中的完整链接文本。"""
        link = (game.get("link") or "").strip() or EPIC_FREE_STORE_ZH
        pic = (game.get("image_url") or "").strip() or DEFAULT_GAME_COVER_URL
        name = game.get("name", "未知游戏")
        if upcoming:
            time_part = self._game_time_info_upcoming(game)
            desc = f"📅 即将免费{time_part}\n\n🔗 完整链接：\n{link}"
            title = f"🔜 {name}"
        else:
            time_part = self._game_time_info_active(game)
            desc = f"🔥 正在免费领取{time_part}\n\n🔗 完整链接：\n{link}\n\n回复「领取」可代领。"
            title = f"🎮 {name}"
        title = title[:WECHAT_ARTICLE_TITLE_MAX]
        desc = desc[:WECHAT_ARTICLE_DESC_MAX]
        return {"title": title, "description": desc, "image": pic, "url": link}

    def _build_passive_articles_merged(
        self, current_games: List[Dict[str, Any]], upcoming_games: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """合并当前免费 + 即将免费，被动图文最多 10 条（微信限制）。"""
        combined: List[tuple] = [(g, False) for g in current_games] + [(g, True) for g in upcoming_games]
        if len(combined) <= MAX_PASSIVE_ARTICLES:
            return [self._game_passive_article(g, upcoming=u) for g, u in combined]

        articles: List[Dict[str, str]] = []
        reserve = 1
        limit = MAX_PASSIVE_ARTICLES - reserve
        for g, u in combined[:limit]:
            articles.append(self._game_passive_article(g, upcoming=u))
        rest = len(combined) - limit
        articles.append({
            "title": f"📋 还有 {rest} 款游戏",
            "description": (
                f"单次消息最多展示 {limit} 款，另有 {rest} 款未列出。\n\n"
                f"🔗 Epic 免费页完整链接：\n{EPIC_FREE_STORE_ZH}"
            )[:WECHAT_ARTICLE_DESC_MAX],
            "image": DEFAULT_GAME_COVER_URL,
            "url": EPIC_FREE_STORE_ZH,
        })
        return articles

    def _get_current_games_message(self) -> Union[str, Dict[str, Any]]:
        """返回游戏展示网页链接，用户点击可查看聚合了图片和文本的游戏页面"""
        games = self._get_active_games()
        upcoming_games = self._get_upcoming_games()

        logger.info(f"游戏查询: 当前免费游戏数量={len(games)}, 即将免费游戏数量={len(upcoming_games)}")

        if games:
            for i, game in enumerate(games):
                logger.info(f"  当前免费游戏 {i+1}: {game.get('name')} (开始: {game.get('start_time')}, 结束: {game.get('end_time')})")
        if upcoming_games:
            for i, game in enumerate(upcoming_games):
                logger.info(f"  即将免费游戏 {i+1}: {game.get('name')} (开始: {game.get('start_time')})")

        if not games and not upcoming_games:
            logger.warning("没有找到任何游戏数据")
            return "当前没有免费游戏信息。\n\n回复'刷新'更新游戏数据。"

        # 构建游戏展示网页链接
        from app.core.config import get_settings
        settings = get_settings()
        
        # 使用域名或IP构建链接
        base_url = settings.WECHAT_OFFICIAL_URL or "http://yxbot.online"
        games_view_url = f"{base_url}/games/view"
        
        # 返回图文消息，引导用户点击链接查看网页
        articles = [{
            "title": f"🎮 本周 {len(games)} 款 Epic 免费游戏",
            "description": f"点击查看本周 {len(games)} 款免费游戏和 {len(upcoming_games)} 款下周预告的详细信息\n\n包含游戏封面、领取时间和直达链接",
            "image": games[0].get("image_url") if games else DEFAULT_GAME_COVER_URL,
            "url": games_view_url
        }]
        
        logger.info(f"生成游戏展示网页链接: {games_view_url}")
        return {"type": "articles", "articles": articles}

    def _get_upcoming_games_message(self) -> Union[str, Dict[str, Any]]:
        games = self._get_upcoming_games()
        if not games:
            return "暂无即将免费的游戏信息。"

        combined = [(g, True) for g in games]
        if len(combined) <= MAX_PASSIVE_ARTICLES:
            articles = [self._game_passive_article(g, upcoming=True) for g in games]
        else:
            articles = []
            limit = MAX_PASSIVE_ARTICLES - 1
            for g in games[:limit]:
                articles.append(self._game_passive_article(g, upcoming=True))
            rest = len(games) - limit
            articles.append({
                "title": f"📋 还有 {rest} 款预告",
                "description": (
                    f"另有 {rest} 款即将免费未列出。\n\n"
                    f"🔗 Epic 免费页完整链接：\n{EPIC_FREE_STORE_ZH}"
                )[:WECHAT_ARTICLE_DESC_MAX],
                "image": DEFAULT_GAME_COVER_URL,
                "url": EPIC_FREE_STORE_ZH,
            })
        return {"type": "articles", "articles": articles}

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

    # ==================== 账号管理 ====================

    def _handle_unbind(self, user) -> str:
        """处理解绑请求"""
        has_auth = user.epic_email or user.epic_device_id or user.epic_refresh_token
        if not has_auth:
            return "您还未绑定 Epic 账号。"
        self.repository.clear_user_epic_account(user)
        return "✅ Epic 账号已解绑。\n\n回复'绑定'可重新绑定。"

    def _get_user_status(self, user) -> str:
        """获取用户状态"""
        lines = ["📊 您的账号状态：\n"]
        lines.append(f"微信 ID：{user.wx_id}")
        lines.append(f"Epic 邮箱：{user.epic_email or '未绑定'}")
        if user.epic_refresh_token:
            auth_type = "Refresh Token（推荐）"
        elif user.epic_device_id:
            auth_type = "Device Auth（旧方式）"
        elif user.epic_password:
            auth_type = "密码（已弃用）"
        else:
            auth_type = "未绑定"
        lines.append(f"认证方式：{auth_type}")
        lines.append(f"账号状态：{'正常' if not user.is_del else '已注销'}")
        if user.epic_refresh_token or user.epic_device_id or user.epic_email:
            lines.append("\n回复'解绑'可解除 Epic 绑定。")
        else:
            lines.append("\n回复'绑定'可绑定 Epic 账号。")
        return "\n".join(lines)

    def _get_help_message(self) -> str:
        """获取帮助消息"""
        return """📖 可用命令：

🎮 游戏相关：
• 游戏 - 图文查看当前免费与预告（图片+链接）
• 下周游戏 - 图文查看即将免费游戏
• 刷新 - 刷新游戏数据

🎁 领取相关：
• 领取 - 自动领取免费游戏（需先绑定）
• 绑定 - 绑定 Epic 账号（浏览器授权）
• 解绑 - 解绑 Epic 账号

ℹ️ 其他：
• 状态 - 查看账号状态
• 帮助 - 查看此帮助信息
• 取消 - 取消当前操作

💡 绑定说明：发送「绑定」后打开链接在浏览器登录 Epic；成功后会收到提示，也可回复「完成」。"""

    # ==================== XML 响应生成 ====================

    def generate_xml_response(self, reply_content: Union[str, Dict[str, Any]], msg: BaseMessage, openid: str = "") -> str:
        if reply_content == "success":
            return "success"

        # 支持图文消息（带图片的游戏查询结果）
        if isinstance(reply_content, dict) and reply_content.get("type") == "articles":
            articles = reply_content["articles"]
            reply = ArticlesReply(message=msg)
            for article in articles:
                reply.add_article(article)
            return reply.render()

        reply = create_reply(reply_content, msg)
        return reply.render()
