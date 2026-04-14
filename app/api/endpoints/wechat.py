from fastapi import APIRouter, Query, Request, Depends, Response, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
import os
import hashlib
from app.security.wechat.wechat_security import WeChatSecurity
from app.services.wechat.message_handler import WeChatService
from wechatpy import parse_message
from app.core.logger import logger
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/wechat/debug/token")
async def debug_wechat_token():
    """
    调试接口：显示当前配置的 Token 信息（仅用于调试）
    """
    token = settings.WECHAT_OFFICIAL_TOKEN
    return JSONResponse({
        "token_length": len(token) if token else 0,
        "token_first5": token[:5] if token and len(token) >= 5 else token,
        "token_last5": token[-5:] if token and len(token) >= 5 else token,
        "appid": settings.WECHAT_OFFICIAL_APPID[:10] if settings.WECHAT_OFFICIAL_APPID else None,
        "aes_key_length": len(settings.WECHAT_OFFICIAL_AES_KEY) if settings.WECHAT_OFFICIAL_AES_KEY else 0,
        "message": "请将此信息与微信公众号后台配置进行对比"
    })


@router.get("/wechat/debug/signature")
async def debug_signature_calculation(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...)
):
    """
    调试接口：验证签名计算过程
    """
    token = settings.WECHAT_OFFICIAL_TOKEN
    
    try:
        tmp_list = [token, timestamp, nonce]
        tmp_list.sort()
        tmp_str = "".join(tmp_list)
        hashstr = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        
        return JSONResponse({
            "token_first5": token[:5] if token and len(token) >= 5 else token,
            "timestamp": timestamp,
            "nonce": nonce,
            "sorted_params": tmp_list,
            "calculated_signature": hashstr,
            "received_signature": signature,
            "match": hashstr == signature,
            "message": "签名匹配" if hashstr == signature else "签名不匹配！请检查微信公众号后台的Token配置"
        })
    except Exception as e:
        return JSONResponse({
            "error": str(e),
            "message": "计算签名时出错"
        }, status_code=500)


@router.get("/wechat/callback/{filename}")
async def serve_wechat_verify_file_from_callback(filename: str):
    """
    微信公众号域名归属权验证文件服务（支持 /wechat/callback/ 路径）
    自动匹配以 MP_verify_ 开头的 .txt 文件
    """
    if filename.startswith("MP_verify_") and filename.endswith(".txt"):
        # 尝试从项目根目录读取验证文件
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            return PlainTextResponse(content)
    raise HTTPException(status_code=404, detail="Not Found")


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
    msg_signature: str = Query(None)
):
    """
    处理微信公众号消息回调 (POST)
    包含：用户发送的消息、事件推送（如关注/取消关注）
    支持明文模式和 AES 加密模式
    """
    logger.info(f"===== 收到微信回调请求 =====")
    logger.info(f"openid: {openid}")
    logger.info(f"encrypt_type: {encrypt_type}")
    logger.info(f"signature: {signature}")
    logger.info(f"timestamp: {timestamp}")
    logger.info(f"nonce: {nonce}")
    
    try:
        # 1. Verify Signature (Security Layer)
        logger.info("步骤1: 开始验证签名")
        WeChatSecurity.verify_signature(signature, timestamp, nonce)
        logger.info("步骤1: 签名验证通过")

        # 2. Get Body & Decrypt if needed (Security Layer)
        logger.info("步骤2: 获取请求体")
        body = await request.body()
        logger.info(f"WeChat callback: encrypt_type={encrypt_type}, openid={openid}, body_len={len(body)}")
        logger.info(f"原始请求体内容: {body[:200] if len(body) > 200 else body}")
        
        if encrypt_type == 'aes':
            logger.info("步骤2: 使用AES解密消息")
            xml_content = WeChatSecurity.decrypt_message(body, msg_signature, timestamp, nonce)
        else:
            logger.info("步骤2: 使用明文模式")
            xml_content = body
        
        logger.info(f"步骤2: 处理后的XML内容: {xml_content[:300] if len(xml_content) > 300 else xml_content}")

        # 3. Parse Message
        logger.info("步骤3: 解析XML消息")
        msg = parse_message(xml_content)
        logger.info(f"步骤3: 消息类型: {msg.type}")
        if hasattr(msg, 'content'):
            logger.info(f"步骤3: 消息内容: {msg.content}")
        if hasattr(msg, 'event'):
            logger.info(f"步骤3: 事件类型: {msg.event}")

        # 4. Process Business Logic (Service Layer)
        logger.info("步骤4: 处理业务逻辑")
        service = WeChatService()
        reply_content = service.process_message(msg, openid)
        logger.info(f"步骤4: 业务处理完成，回复内容类型: {type(reply_content).__name__}")
        
        # 5. Generate Response (Service Layer / Controller Layer)
        if reply_content == "success":
            logger.info("步骤5: 返回success响应")
            return Response(content="success")
            
        logger.info("步骤5: 生成XML响应")
        xml_response = service.generate_xml_response(reply_content, msg, openid=openid)
        logger.info(f"WeChat response: type={type(reply_content).__name__}, xml_len={len(xml_response)}")
        logger.info(f"步骤5: XML响应内容: {xml_response[:300] if len(xml_response) > 300 else xml_response}")

        # 6. Encrypt Response if needed (Security Layer)
        if encrypt_type == 'aes':
            logger.info("步骤6: 加密响应")
            xml_response = WeChatSecurity.encrypt_message(xml_response, timestamp, nonce)
        
        logger.info("===== 微信回调处理完成 =====")
        return Response(content=xml_response, media_type="application/xml")
    
    except HTTPException as e:
        logger.error(f"微信回调HTTP异常: status_code={e.status_code}, detail={e.detail}", exc_info=True)
        # Return success to WeChat to avoid retries even if our processing failed
        return Response(content="success")
    except Exception as e:
        logger.error(f"Error processing WeChat message: {e}", exc_info=True)
        # Return success to WeChat to avoid retries even if our processing failed
        return Response(content="success")
