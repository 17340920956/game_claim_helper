from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from datetime import datetime, timedelta
import jwt
from typing import Optional, Dict, Any
from app.core.config import get_settings

settings = get_settings()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_admin_access(api_key: str = Security(api_key_header)):
    """
    验证管理员 API Key
    用于保护敏感接口（如刷新游戏、查看用户列表等）
    """
    if api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的 API Key"
        )
    return True

def create_confirmation_token(user_id: int, game_slug: str, action: str = "confirmed") -> str:
    """
    生成确认操作的 JWT Token
    该 Token 将嵌入到推送消息的链接中，用户点击后无需登录即可确认
    包含字段：
    - sub: 用户 ID
    - game_slug: 游戏标识符
    - action: 动作类型 (confirmed/claimed)
    - exp: 过期时间
    - type: Token 类型标识
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "game_slug": game_slug,
        "action": action,
        "exp": expire,
        "type": "confirmation"
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_confirmation_token(token: str) -> Dict[str, Any]:
    """
    验证确认操作的 JWT Token
    解析 Token 并检查有效性（签名、过期时间、类型）
    返回解码后的 payload
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "confirmation":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 Token 类型"
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token"
        )
