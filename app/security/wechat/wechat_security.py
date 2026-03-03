from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
from fastapi import HTTPException
from app.core.config import get_settings
from app.core.logger import logger

settings = get_settings()

class WeChatSecurity:
    @staticmethod
    def verify_signature(signature: str, timestamp: str, nonce: str):
        token = settings.WECHAT_OFFICIAL_TOKEN
        if not token:
            raise HTTPException(status_code=500, detail="Token not configured")
        try:
            check_signature(token, signature, timestamp, nonce)
        except InvalidSignatureException:
            logger.warning(f"微信签名校验失败: signature={signature}, timestamp={timestamp}, nonce={nonce}")
            raise HTTPException(status_code=403, detail="Invalid signature")

    @staticmethod
    def decrypt_message(body: bytes, msg_signature: str, timestamp: str, nonce: str) -> str:
        token = settings.WECHAT_OFFICIAL_TOKEN
        aes_key = settings.WECHAT_OFFICIAL_AES_KEY
        appid = settings.WECHAT_OFFICIAL_APPID
        
        try:
            crypto = WeChatCrypto(token, aes_key, appid)
            decrypted_xml = crypto.decrypt_message(
                body,
                msg_signature,
                timestamp,
                nonce
            )
            return decrypted_xml
        except InvalidSignatureException:
            raise HTTPException(status_code=403, detail="Invalid signature")

    @staticmethod
    def encrypt_message(xml: str, timestamp: str, nonce: str) -> str:
        token = settings.WECHAT_OFFICIAL_TOKEN
        aes_key = settings.WECHAT_OFFICIAL_AES_KEY
        appid = settings.WECHAT_OFFICIAL_APPID
        
        crypto = WeChatCrypto(token, aes_key, appid)
        return crypto.encrypt_message(xml, nonce, timestamp)
