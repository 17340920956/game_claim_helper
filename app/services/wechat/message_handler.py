from sqlalchemy.orm import Session
from app.repositories.wechat.wechat_repository import WeChatRepository
from wechatpy import create_reply
from wechatpy.messages import BaseMessage
from app.core.logger import logger

class WeChatService:
    def __init__(self, db: Session):
        self.repository = WeChatRepository(db)

    def process_message(self, msg: BaseMessage, openid: str) -> str:
        """
        Process the parsed message and return reply content (text)
        """
        reply_content = "收到"
        user = self.repository.get_user_by_openid(openid)

        if not user:
            user = self.repository.create_user(openid)
            logger.info(f"New WeChat user created: {openid}")
            reply_content = "欢迎关注！您的账号已自动创建。"
        else:
            if user.is_del:
                self.repository.update_user_active_status(user, True)
                reply_content = "欢迎回来！"

        if msg.type == 'text':
             logger.info(f"Received message from {openid}: {msg.content}")
             # Here we could add logic to handle specific keywords
        elif msg.type == 'event':
            if msg.event == 'subscribe':
                logger.info(f"User subscribed: {openid}")
                reply_content = "感谢关注！"
            elif msg.event == 'unsubscribe':
                logger.info(f"User unsubscribed: {openid}")
                if user:
                    self.repository.update_user_active_status(user, False)
                return "success" # No reply needed for unsubscribe

        return reply_content

    def generate_xml_response(self, reply_content: str, msg: BaseMessage) -> str:
        if reply_content == "success":
            return "success"
            
        reply = create_reply(reply_content, msg)
        return reply.render()
