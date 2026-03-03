
import requests
from typing import Optional, Dict, Any, List
from wechatpy.client import WeChatClient
from wechatpy.client.api.base import BaseWeChatAPI
from wechatpy.exceptions import WeChatClientException
from app.db.redis import redis_client
from app.core.config import get_settings
from app.core.logger import logger
from app.utils.wechat.constants import WeChatErrorCode

settings = get_settings()

class CustomWeChatClient(WeChatClient):
    """
    Custom WeChatClient to support stable access token and additional APIs
    """
    
    def __init__(self, appid, secret, access_token=None, session=None, timeout=None, auto_retry=True):
        super().__init__(appid, secret, access_token, session, timeout, auto_retry)
        # Initialize custom APIs
        self.misc = CustomMisc(self)
        self.redis_key = f"wechat_stable_token:{appid}"

    @property
    def access_token(self):
        # 1. Check Redis
        token = redis_client.client.get(self.redis_key)
        if token:
            logger.info(f"[WeChat] Using cached access token from Redis: {token[:10]}... (Key: {self.redis_key})")
            return token
        
        logger.info(f"[WeChat] No cached token found. Fetching new one... (Key: {self.redis_key})")
        # 2. Fetch new
        self.fetch_access_token()
        # 3. Return from Redis
        return redis_client.client.get(self.redis_key)

    def _fetch_access_token(self, url, params):
        """
        Override _fetch_access_token to use getStableAccessToken
        """
        # The original method uses GET with params, we need POST for stable token
        # We ignore the url and params passed by the parent and use our own
        
        api_url = settings.WECHAT_OFFICIAL_STABLE_TOKEN_URL
        logger.info(f"[WeChat] Requesting stable token from: {api_url}")
        
        payload = {
            "grant_type": "client_credential",
            "appid": self.appid,
            "secret": self.secret,
            "force_refresh": False
        }
        
        response = requests.post(api_url, json=payload, timeout=self.timeout)
        result = response.json()
        
        if "errcode" in result and result["errcode"] != 0:
            err_msg = WeChatErrorCode.get_message(result["errcode"])
            logger.error(f"[WeChat] Token fetch failed: {result} - {err_msg}")
            raise WeChatClientException(
                result["errcode"],
                result.get("errmsg"),
                client=self,
                request=response.request,
                response=response
            )
            
        # Save token to Redis with 7000s expiration
        access_token = result['access_token']
        expires_in = 7000
        
        logger.info(f"[WeChat] Token fetched successfully. Caching to Redis (Key: {self.redis_key}, TTL: {expires_in}s)")
        
        redis_client.client.set(
            self.redis_key,
            access_token,
            ex=expires_in
        )
        
        # Also update session for compatibility if needed, though we primarily use Redis now
        if self.session:
            self.session.set(
                self.access_token_key,
                access_token,
                expires_in
            )
        
        return result

class CustomMisc(BaseWeChatAPI):
    def callback_check(self, action="all", check_operator="DEFAULT"):
        """
        Network detection / Callback check
        Docs: https://developers.weixin.qq.com/doc/subscription/api/base/api_callbackcheck.html
        Config: WECHAT_OFFICIAL_CALLBACK_CHECK_URL
        """
        # Extract path from configured URL to use with wechatpy
        return self._post(
            settings.WECHAT_OFFICIAL_CALLBACK_CHECK_URL.split("cgi-bin/")[-1],
            data={
                "action": action,
                "check_operator": check_operator
            }
        )

