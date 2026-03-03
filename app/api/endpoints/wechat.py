from fastapi import APIRouter, Query, Request, Depends, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.security.wechat.wechat_security import WeChatSecurity
from app.services.wechat.message_handler import WeChatService
from wechatpy import parse_message
from app.core.logger import logger

router = APIRouter()

@router.get("/wechat/callback")
async def wechat_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """
    微信公众号服务器配置验证接口 (GET)
    微信服务器会发送 GET 请求来验证服务器有效性
    需要对 signature 进行校验，通过后原样返回 echostr
    """
    WeChatSecurity.verify_signature(signature, timestamp, nonce)
    return Response(content=echostr)

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
    """
    处理微信公众号消息回调 (POST)
    包含：用户发送的消息、事件推送（如关注/取消关注）
    支持明文模式和 AES 加密模式
    """
    try:
        # 1. Verify Signature (Security Layer)
        WeChatSecurity.verify_signature(signature, timestamp, nonce)

        # 2. Get Body & Decrypt if needed (Security Layer)
        body = await request.body()
        if encrypt_type == 'aes':
            xml_content = WeChatSecurity.decrypt_message(body, msg_signature, timestamp, nonce)
        else:
            xml_content = body

        # 3. Parse Message
        msg = parse_message(xml_content)

        # 4. Process Business Logic (Service Layer)
        service = WeChatService(db)
        reply_content = service.process_message(msg, openid)
        
        # 5. Generate Response (Service Layer / Controller Layer)
        if reply_content == "success":
            return Response(content="success")
            
        xml_response = service.generate_xml_response(reply_content, msg)

        # 6. Encrypt Response if needed (Security Layer)
        if encrypt_type == 'aes':
            xml_response = WeChatSecurity.encrypt_message(xml_response, timestamp, nonce)

        return Response(content=xml_response, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"Error processing WeChat message: {e}")
        # Return success to WeChat to avoid retries even if our processing failed
        return Response(content="success")
