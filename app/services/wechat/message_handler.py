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

    def _handle_text_message(self, user_id: int, openid: str, content: str, user) -> Union[str, Dict[str, Any]]:
        """处理文本消息"""

        # 统一取消命令（任何状态下都能触发）
        if content.strip().lower() in ('取消', '退出', 'cancel', 'quit', 'q'):
            state = self._get_state(user_id)
            if state:
                self._clear_state(user_id)
                return "操作已取消。\n\n回复'帮助'查看可用命令。"

        # 优先检查用户多轮对话状态
        state = self._get_state(user_id)
        if state:
            return self._handle_state_message(user_id, openid, content, user, state)

        # 命令映射
        content_lower = content.lower()
        commands = {
            frozenset(['帮助', 'help', '?']): self._get_help_message,
            frozenset(['确认', '收到']): lambda: "收到确认，感谢您的回复！",
            frozenset(['领取', '领取游戏']): lambda: self._handle_claim_request(user),
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
                    return self._handle_bind_request(user)
                return handler() if handler else "收到"

        return "收到您的消息！\n\n回复'帮助'查看可用命令。"

    # ==================== 多轮对话处理 ====================

    def _handle_state_message(self, user_id: int, openid: str, content: str, user, state: dict) -> str:
        """处理多轮对话状态"""
        step = state.get('step')

        if step == 'waiting_device_auth':
            if content.strip().lower() in ('完成', '好了', 'ok', 'yes', '是'):
                # 用户声称已完成授权，主动检查一次
                device_code = state.get('device_code')
                if device_code:
                    try:
                        auth_result = epic_claim_service.poll_device_code(device_code, timeout=10, interval=3)
                        # 授权成功！处理绑定
                        access_token = auth_result["access_token"]
                        refresh_token = auth_result.get("refresh_token")
                        account_id = auth_result["account_id"]
                        email = self._get_epic_email(access_token, account_id)

                        # 创建 Device Auth
                        device_auth = None
                        try:
                            device_auth = epic_claim_service.create_device_auth(access_token, account_id)
                        except Exception as e:
                            logger.warning(f"Failed to create Device Auth: {e}")

                        # 保存到数据库
                        self._save_binding_to_db(user_id, account_id, email, refresh_token, device_auth)

                        # 清除状态
                        self._clear_state(user_id)
                        return f"✅ Epic 账号绑定成功！\n📧 邮箱：{email or '已关联'}\n\n回复'领取'让我们帮您领取免费游戏。"
                    except Exception as e:
                        logger.info(f"User claimed done but auth not ready: {e}")
                        return "⏳ 还未检测到授权成功，请确认已在浏览器中完成登录。\n\n稍后再回复'完成'，或回复'取消'退出。"
            # 其他消息提示等待
            return "⏳ 请先在浏览器中完成 Epic 账号授权。\n\n授权完成后回复'完成'，回复'取消'退出绑定流程。"

        elif step == 'confirm_device_auth':
            if content.strip().lower() in ('完成', '好了', 'ok', 'yes', '是'):
                # 后台轮询已检测到授权成功，直接完成绑定
                return self._complete_binding(user, user_id, state)
            elif content.strip().lower() in ('取消', '退出', 'cancel', 'quit'):
                self._clear_state(user_id)
                return "已取消绑定。\n\n回复'绑定'可重新开始。"
            else:
                return "⏳ 请先在浏览器中完成 Epic 授权，然后回复'完成'确认。\n\n回复'取消'退出绑定流程。"

        else:
            self._clear_state(user_id)
            return "操作已超时或无效。\n\n回复'帮助'查看可用命令。"

    # ==================== 绑定相关 ====================

    def _handle_bind_request(self, user) -> str:
        """处理绑定请求 - 使用 Device Code 流程"""
        # 检查是否已绑定（有 refresh_token 或旧的 device_auth）
        has_auth = user.epic_refresh_token or (user.epic_device_id and user.epic_device_secret)
        if has_auth:
            return f"您已绑定 Epic 账号（{user.epic_email or '已关联'}）。\n\n回复'解绑'可先解除绑定再重新绑定。"

        return self._handle_bind_request_with_message(user)

    def _handle_bind_request_with_message(self, user, prefix_msg: str = "") -> str:
        """处理绑定请求的内部实现，支持自定义前缀消息"""
        try:
            device_code_data = epic_claim_service.create_device_code()
            verification_uri = device_code_data.get("verification_uri_complete", "")
            user_code = device_code_data.get("user_code", "")

            if not verification_uri:
                return "❌ 获取授权链接失败，请稍后再试。"

            # 保存 device_code 到状态
            self._set_state(user.id, {
                'step': 'waiting_device_auth',
                'device_code': device_code_data.get("device_code"),
                'user_code': user_code,
            })

            # 启动后台轮询线程
            self._start_background_poll(user.id, device_code_data.get("device_code"))

            bind_message = (
                f"🔗 请点击以下链接完成 Epic 账号授权：\n\n"
                f"{verification_uri}\n\n"
                f"授权码：{user_code}\n\n"
                f"请在10分钟内完成授权，完成后回复'完成'。\n"
                f"回复'取消'退出绑定流程。"
            )

            return prefix_msg + bind_message
        except Exception as e:
            logger.error(f"创建 Device Code 失败: {e}")
            return "❌ 获取授权链接失败，请稍后再试。"

    def _start_background_poll(self, user_id: int, device_code: str):
        """启动后台线程轮询 Device Code 授权状态"""
        def poll():
            try:
                auth_result = epic_claim_service.poll_device_code(device_code, timeout=540, interval=10)
                # 授权成功
                access_token = auth_result["access_token"]
                refresh_token = auth_result.get("refresh_token")
                account_id = auth_result["account_id"]

                # 获取用户邮箱
                email = self._get_epic_email(access_token, account_id)

                # 创建 Device Auth 凭证（长期有效，优先使用）
                device_auth = None
                try:
                    device_auth = epic_claim_service.create_device_auth(access_token, account_id)
                    logger.info(f"Background poll: Device Auth created for user {user_id}")
                except Exception as e:
                    logger.warning(f"Background poll: Failed to create Device Auth: {e}")

                # 保存到数据库
                self._save_binding_to_db(user_id, account_id, email, refresh_token, device_auth)

                # 更新 Redis 状态为已确认
                self._set_state(user_id, {
                    'step': 'confirm_device_auth',
                    'device_code': device_code,
                    'email': email,
                })
            except Exception as e:
                logger.info(f"Background poll: User {user_id} device code expired or failed: {e}")

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

    def _complete_binding(self, user, user_id: int, state: dict) -> str:
        """完成绑定流程"""
        email = state.get('email')
        self._clear_state(user_id)
        logger.info(f"User {user_id} bound Epic account: {email}")
        return f"✅ Epic 账号绑定成功！\n📧 邮箱：{email or '已关联'}\n\n回复'领取'让我们帮您领取免费游戏。"

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

    def _handle_claim_request(self, user) -> str:
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
                f"请重新绑定以继续领取游戏：\n\n"
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
            )

            logger.info(f"Claim result for {game_name}: success={result.get('success')}, "
                       f"message={result.get('message')}")

            # 如果领取成功且返回了新的 refresh_token，更新数据库
            if result.get("new_refresh_token"):
                try:
                    self.repository.update_user_refresh_token(user, result["new_refresh_token"])
                    logger.info(f"Updated refresh token for user {user.id}")
                except Exception as e:
                    logger.warning(f"Failed to update refresh token for user {user.id}: {e}")

            if result["success"]:
                msg = f"✅ 领取「{game_name}」成功！{result.get('message', '')}"
                logger.info(f"用户 {user.id} 领取游戏 {game_name} 成功")
            else:
                msg = f"❌ 领取「{game_name}」失败：{result.get('message', '未知错误')}"
                logger.warning(f"用户 {user.id} 领取游戏 {game_name} 失败: {msg}")

            return msg
        except Exception as e:
            logger.exception(f"领取游戏异常: {e}")
            return f"❌ 领取「{game_name}」时发生异常：{str(e)}"

    # ==================== 游戏查询 ====================

    def _get_current_games_message(self) -> Union[str, Dict[str, Any]]:
        """获取当前免费游戏消息
        
        策略：
        - 被动回复纯文本消息（展示所有游戏信息+链接），确保所有游戏都能完整展示
        - 后台尝试用客服消息逐条发送图文消息（带图片），如果 AppSecret 有效则用户额外收到图文
        """
        games = self._get_active_games()
        upcoming_games = self._get_upcoming_games()

        if not games and not upcoming_games:
            return "当前没有免费游戏信息。"

        # 构建纯文本消息（被动回复，确保可靠展示所有游戏）
        text_msg = self._build_games_text(games, upcoming_games)

        # 构建图文列表（后台客服消息发送，带图片）
        all_articles = []
        for game in games:
            time_info = ""
            start_time_str = game.get("start_time")
            end_time_str = game.get("end_time")
            if start_time_str and end_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                    time_info = f"\n免费时间：{_format_time(start_time)} ~ {_format_time(end_time)}"
                except Exception:
                    pass
            all_articles.append({
                "title": f"🎮 {game.get('name', '未知游戏')}",
                "description": f"🔥 正在免费领取！{time_info}\n\n回复'领取'让我们帮您领取游戏。",
                "url": game.get("link", "https://store.epicgames.com/en-US/free-games"),
                "image": game.get("image_url", ""),
            })

        for game in upcoming_games:
            time_info = ""
            start_time_str = game.get("start_time")
            end_time_str = game.get("end_time")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    time_info = f"\n开始时间：{_format_time(start_time)}"
                    if end_time_str:
                        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                        time_info += f" ~ {_format_time(end_time)}"
                except Exception:
                    pass
            all_articles.append({
                "title": f"🔜 {game.get('name', '未知游戏')}",
                "description": f"📅 即将免费！{time_info}\n\n敬请期待！",
                "url": game.get("link", "https://store.epicgames.com/en-US/free-games"),
                "image": game.get("image_url", ""),
            })

        # 返回带后台发送信息的结果
        return {"type": "text_with_articles", "text": text_msg, "articles_to_send": all_articles}

    def _get_upcoming_games_message(self) -> Union[str, Dict[str, Any]]:
        """获取即将免费游戏消息"""
        games = self._get_upcoming_games()
        if not games:
            return "暂无即将免费的游戏信息。"

        # 纯文本消息
        text_msg = self._build_upcoming_text(games)

        # 图文列表
        articles = []
        for game in games:
            time_info = ""
            start_time_str = game.get("start_time")
            end_time_str = game.get("end_time")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    time_info = f"\n开始时间：{_format_time(start_time)}"
                    if end_time_str:
                        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                        time_info += f" ~ {_format_time(end_time)}"
                except Exception:
                    pass
            articles.append({
                "title": f"🔜 {game.get('name', '未知游戏')}",
                "description": f"📅 即将免费！{time_info}\n\n敬请期待！",
                "url": game.get("link", "https://store.epicgames.com/en-US/free-games"),
                "image": game.get("image_url", ""),
            })

        return {"type": "text_with_articles", "text": text_msg, "articles_to_send": articles}

    def _build_games_text(self, games: List[Dict], upcoming_games: List[Dict]) -> str:
        """构建所有游戏的纯文本消息（降级方案）"""
        lines = []
        if games:
            lines.append("🎮 当前免费游戏：")
            for i, game in enumerate(games, 1):
                time_info = ""
                start_time_str = game.get("start_time")
                end_time_str = game.get("end_time")
                if start_time_str and end_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                        time_info = f"（{_format_time(start_time)} ~ {_format_time(end_time)}）"
                    except Exception:
                        pass
                link = game.get("link", "")
                lines.append(f"🔥 {i}. {game.get('name', '未知游戏')} {time_info}")
                if link:
                    lines.append(f"🔗 {link}")
            lines.append("")

        if upcoming_games:
            lines.append("🔜 即将免费：")
            for i, game in enumerate(upcoming_games, 1):
                time_info = ""
                start_time_str = game.get("start_time")
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                        time_info = f"（开始：{_format_time(start_time)}）"
                    except Exception:
                        pass
                link = game.get("link", "")
                lines.append(f"📅 {i}. {game.get('name', '未知游戏')} {time_info}")
                if link:
                    lines.append(f"🔗 {link}")
            lines.append("")
        
        lines.append("回复'领取'让我们帮您领取游戏。")
        return "\n".join(lines)

    def _build_upcoming_text(self, games: List[Dict]) -> str:
        """构建即将免费游戏的纯文本消息"""
        lines = ["🔜 即将免费的游戏："]
        for i, game in enumerate(games, 1):
            time_info = ""
            start_time_str = game.get("start_time")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    time_info = f"（开始：{_format_time(start_time)}）"
                except Exception:
                    pass
            link = game.get("link", "")
            lines.append(f"📅 {i}. {game.get('name', '未知游戏')} {time_info}")
            if link:
                lines.append(f"🔗 {link}")
        lines.append("")
        lines.append("敬请期待！")
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
• 游戏 - 查看当前免费游戏（带图片）
• 下周游戏 - 查看即将免费游戏
• 刷新 - 刷新游戏数据

🎁 领取相关：
• 领取 - 自动领取免费游戏（需先绑定）
• 绑定 - 绑定 Epic 账号（浏览器授权）
• 解绑 - 解绑 Epic 账号

ℹ️ 其他：
• 状态 - 查看账号状态
• 帮助 - 查看此帮助信息
• 取消 - 取消当前操作

💡 绑定说明：发送'绑定'后会收到一个授权链接，在浏览器中登录 Epic 即可完成绑定。"""

    # ==================== XML 响应生成 ====================

    def generate_xml_response(self, reply_content: Union[str, Dict[str, Any]], msg: BaseMessage, openid: str = "") -> str:
        if reply_content == "success":
            return "success"

        # 文本+后台图文消息：被动回复文本，后台客服消息发图文
        if isinstance(reply_content, dict) and reply_content.get("type") == "text_with_articles":
            text = reply_content["text"]
            articles_to_send = reply_content.get("articles_to_send", [])
            
            # 后台发送图文消息
            if articles_to_send and openid:
                self._send_articles_async(openid, articles_to_send)
            
            # 被动回复纯文本消息
            reply = create_reply(text, msg)
            return reply.render()

        # 支持图文消息（带图片的游戏查询结果）
        if isinstance(reply_content, dict) and reply_content.get("type") == "articles":
            articles = reply_content["articles"]
            reply = ArticlesReply(message=msg)
            for article in articles:
                reply.add_article(article)
            return reply.render()

        reply = create_reply(reply_content, msg)
        return reply.render()

    def _send_articles_async(self, openid: str, articles: List[Dict]):
        """后台线程通过客服消息逐条发送图文消息"""
        def send():
            from app.services.wechat.push_sender import WeChatOfficialPusher
            pusher = WeChatOfficialPusher()
            
            for article in articles:
                try:
                    result = pusher.send_news_message(openid, [article])
                    if result.get("success"):
                        logger.info(f"Sent article via customer service: {article.get('title', '')}")
                    else:
                        logger.warning(f"Failed to send article: {result}")
                except Exception as e:
                    logger.error(f"Failed to send article via customer service: {e}")

        thread = threading.Thread(target=send, daemon=True)
        thread.start()
