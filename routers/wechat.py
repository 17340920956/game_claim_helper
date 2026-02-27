from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.responses import PlainTextResponse
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.crypto import WeChatCrypto
from sqlalchemy.orm import Session
from datetime import datetime

from config import get_settings
from db.connection import get_db
from db.models import User, PushLog, ContactType, ConfirmationStatus
from services.notification.service import push_service
from db.redis import redis_client

router = APIRouter()
settings = get_settings()

@router.get("/wechat/callback")
async def wechat_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    token = settings.WECHAT_OFFICIAL_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="Token not configured")
        
    try:
        check_signature(token, signature, timestamp, nonce)
        return Response(content=echostr)
    except InvalidSignatureException:
        raise HTTPException(status_code=403, detail="Invalid signature")

@router.post("/wechat/callback")
async def wechat_callback(
    request: Request,
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    openid: str = Query(...),
    encrypt_type: str = Query(None),
    msg_signature: str = Query(None),
    db: Session = Depends(get_db)
):
    token = settings.WECHAT_OFFICIAL_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="Token not configured")

    # Read body
    body = await request.body()
    
    # Check signature
    try:
        check_signature(token, signature, timestamp, nonce)
    except InvalidSignatureException:
        raise HTTPException(status_code=403, detail="Invalid signature")

    if encrypt_type == 'aes':
        # 解密消息
        try:
            crypto = WeChatCrypto(
                token,
                settings.WECHAT_OFFICIAL_AES_KEY,
                settings.WECHAT_OFFICIAL_APPID
            )
            decrypted_xml = crypto.decrypt_message(
                body,
                msg_signature,
                timestamp,
                nonce
            )
            msg = parse_message(decrypted_xml)
        except InvalidSignatureException:
            raise HTTPException(status_code=403, detail="Invalid signature")
    else:
        # 明文消息
        msg = parse_message(body)

    # Auto reply logic
    reply = None
    if msg.type == 'text':
        content = msg.content.strip()
        reply_content = ""
        
        if content == '确认':
            # 处理确认逻辑
            user = db.query(User).filter(
                User.contact_type == ContactType.wechat_official,
                User.contact_id == openid
            ).first()
            
            if user:
                # 查找最近一条待确认的消息
                push_log = db.query(PushLog).filter(
                    PushLog.user_id == user.id,
                    PushLog.confirmation_status == ConfirmationStatus.pending
                ).order_by(PushLog.created_at.desc()).first()
                
                if push_log:
                    push_log.confirmation_status = ConfirmationStatus.confirmed
                    push_log.confirmation_time = datetime.now()
                    db.commit()
                    
                    try:
                        redis_client.update_user_status(
                            push_log.game_slug, 
                            user.id, 
                            "confirmed",
                            is_next_week=push_log.is_next_week
                        )
                    except Exception as e:
                        print(f"Redis update failed: {e}")
                    
                    reply_content = f"已收到您的确认！\n游戏：{push_log.game_title}"
                else:
                    reply_content = "当前没有待确认的消息。"
            else:
                reply_content = "您尚未绑定账号，请先绑定。"
                
        elif content == '领取':
            # 处理领取逻辑
            user = db.query(User).filter(
                User.contact_type == ContactType.wechat_official,
                User.contact_id == openid
            ).first()
            
            if user:
                # 查找最近一条待确认或已确认的消息
                push_log = db.query(PushLog).filter(
                    PushLog.user_id == user.id,
                    PushLog.confirmation_status.in_([ConfirmationStatus.pending, ConfirmationStatus.confirmed])
                ).order_by(PushLog.created_at.desc()).first()
                
                if push_log:
                    push_log.confirmation_status = ConfirmationStatus.claimed
                    push_log.confirmation_time = datetime.now()
                    db.commit()
                    
                    try:
                        redis_client.update_user_status(
                            push_log.game_slug, 
                            user.id, 
                            "claimed",
                            is_next_week=push_log.is_next_week
                        )
                    except Exception as e:
                        print(f"Redis update failed: {e}")
                    
                    reply_content = f"标记为已领取！\n游戏：{push_log.game_title}"
                else:
                    reply_content = "当前没有可领取的游戏消息。"
            else:
                reply_content = "您尚未绑定账号，请先绑定。"
        else:
            reply_content = "收到您的消息，请回复'确认'或'领取'。"

        reply = create_reply(reply_content, msg)
            
    elif msg.type == 'event':
        if msg.event == 'subscribe':
            reply = create_reply('欢迎关注Epic免费游戏助手！\n我们会每周推送免费游戏信息。\n请回复"确认"或"领取"与系统交互。', msg)
    
    if not reply:
        return Response(content="success")
        
    xml = reply.render()
    
    if encrypt_type == 'aes':
        crypto = WeChatCrypto(
            token,
            settings.WECHAT_OFFICIAL_AES_KEY,
            settings.WECHAT_OFFICIAL_APPID
        )
        xml = crypto.encrypt_message(xml, nonce, timestamp)
    
    return Response(content=xml, media_type="application/xml")
