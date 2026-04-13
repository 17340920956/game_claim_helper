from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
from fastapi import HTTPException
from app.core.config import get_settings
from app.core.logger import logger
import hashlib

settings = get_settings()

class WeChatSecurity:
    @staticmethod
    def verify_signature(signature: str, timestamp: str, nonce: str):
        token = settings.WECHAT_OFFICIAL_TOKEN
        if not token:
            logger.error("WECHAT_OFFICIAL_TOKEN 未配置！")
            raise HTTPException(status_code=500, detail="Token not configured")
        
        logger.info(f"微信签名校验 - token(前5位): {token[:5] if len(token)>=5 else token}, signature: {signature}, timestamp: {timestamp}, nonce: {nonce}")
        
        try:
            check_signature(token, signature, timestamp, nonce)
            logger.info("微信签名校验成功")
        except InvalidSignatureException as e:
            logger.warning(f"微信签名校验失败: signature={signature}, timestamp={timestamp}, nonce={nonce}")
            logger.warning(f"配置的 token(前5位): {token[:5] if len(token)>=5 else token}")
            
            try:
                tmp_list = [token, timestamp, nonce]
                tmp_list.sort()
                tmp_str = "".join(tmp_list)
                hashstr = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
                logger.warning(f"本地计算的签名: {hashstr}")
                logger.warning(f"微信传来的签名: {signature}")
            except Exception as calc_e:
                logger.warning(f"计算本地签名时出错: {calc_e}")
            
            raise HTTPException(status_code=403, detail="Invalid signature")

    @staticmethod
    def decrypt_message(body: bytes, msg_signature: str, timestamp: str, nonce: str) -> str:
        token = settings.WECHAT_OFFICIAL_TOKEN
        aes_key = settings.WECHAT_OFFICIAL_AES_KEY
        appid = settings.WECHAT_OFFICIAL_APPID
        
        logger.info(f"解密消息 - appid(前5位): {appid[:5] if len(appid)>=5 else appid}, msg_signature: {msg_signature}")
        
        try:
            crypto = WeChatCrypto(token, aes_key, appid)
            decrypted_xml = crypto.decrypt_message(
                body,
                msg_signature,
                timestamp,
                nonce
            )
            logger.info(f"消息解密成功，解密后的内容长度: {len(decrypted_xml)}")
            return decrypted_xml
        except InvalidSignatureException as e:
            logger.error(f"解密消息时签名校验失败: {e}")
            raise HTTPException(status_code=403, detail="Invalid signature")
        except Exception as e:
            logger.error(f"解密消息时发生未知错误: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Decryption error")

    @staticmethod
    def encrypt_message(xml: str, timestamp: str, nonce: str) -> str:
        token = settings.WECHAT_OFFICIAL_TOKEN
        aes_key = settings.WECHAT_OFFICIAL_AES_KEY
        appid = settings.WECHAT_OFFICIAL_APPID
        
        logger.info(f"加密消息 - appid(前5位): {appid[:5] if len(appid)>=5 else appid}")
        
        try:
            crypto = WeChatCrypto(token, aes_key, appid)
            encrypted = crypto.encrypt_message(xml, nonce, timestamp)
            logger.info(f"消息加密成功，加密后的内容长度: {len(encrypted)}")
            return encrypted
        except Exception as e:
            logger.error(f"加密消息时发生错误: {e}", exc_info=True)
            raise
