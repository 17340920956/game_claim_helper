"""
密码加密/解密工具
使用 Fernet 对称加密存储 Epic 账号密码
"""
from cryptography.fernet import Fernet
from app.core.config import get_settings

settings = get_settings()


def get_fernet() -> Fernet:
    """获取 Fernet 实例，使用 SECRET_KEY 派生"""
    key = settings.SECRET_KEY
    if len(key) < 32:
        key = key.ljust(32, "0")
    key_bytes = key[:32].encode("utf-8")
    import base64
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_password(plain_password: str) -> str:
    """加密密码"""
    if not plain_password:
        return ""
    f = get_fernet()
    return f.encrypt(plain_password.encode("utf-8")).decode("utf-8")


def decrypt_password(encrypted_password: str) -> str:
    """解密密码"""
    if not encrypted_password:
        return ""
    f = get_fernet()
    return f.decrypt(encrypted_password.encode("utf-8")).decode("utf-8")
