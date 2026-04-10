"""
Epic Games 自动领取服务
通过 Device Code + Device Auth 认证并领取免费游戏

认证流程：
1. 用 fortniteNewSwitchGameClient 获取 client_credentials token
2. 用该 token 创建 deviceAuthorization（Device Code）
3. 用户在浏览器中授权
4. 用 device_code 获取 access_token + refresh_token
5. 用 access_token 创建 Device Auth 凭证（长期有效）
6. 后续领取用 Device Auth 登录获取 access_token

客户端说明：
- fortniteNewSwitchGameClient: 支持 client_credentials + device_code grant type
- fortniteAndroidGameClient: 支持 device_auth grant type（用于 Device Auth 登录）
"""
import requests
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.core.logger import logger
from app.core.crypto import decrypt_password, encrypt_password


# Epic 登录相关常量
EPIC_AUTH_API = "https://account-public-service-prod.ol.epicgames.com"
EPIC_LAUNCHER_API = "https://launcher-public-service-prod.ol.epicgames.com"
EPIC_GRAPHQL_URL = "https://graphql.epicgames.com/graphql"
EPIC_ORDER_API = "https://store-site-backend-static.ak.epicgames.com"

# fortniteNewSwitchGameClient 凭证（支持 client_credentials + device_code）
SWITCH_AUTH_BASIC = "OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"

# fortniteAndroidGameClient 凭证（支持 device_auth grant type）
# 旧客户端ID已失效，使用新的客户端ID
# ANDROID_AUTH_BASIC = "M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU="
# 使用 fortniteNewSwitchGameClient 作为备用（支持 refresh_token）
ANDROID_AUTH_BASIC = "OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"

# Epic 登录 Headers
EPIC_AUTH_HEADERS = {
    "User-Agent": "Fortnite/++Fortnite+Release-31.00-CL-33594855 Android/12",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*",
}

# GraphQL 购买 Mutation
PURCHASE_MUTATION = """
mutation purchaseGame($input: PurchaseGameInput!) {
    PurchaseGame(input: $input) {
        order {
            id
            state
            totalPrice {
                discountPrice
                originalPrice
            }
        }
        purchaseSuccess
    }
}
"""


class EpicClaimError(Exception):
    """Epic 领取异常"""
    pass


class EpicClaimService:
    """Epic 免费游戏自动领取服务"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(EPIC_AUTH_HEADERS)

    def get_client_token(self) -> str:
        """获取 client_credentials token（用于创建 device code）"""
        try:
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/token",
                headers={
                    **EPIC_AUTH_HEADERS,
                    "Authorization": f"basic {SWITCH_AUTH_BASIC}",
                },
                data={
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
            return resp.json().get("access_token")
        except Exception as e:
            raise EpicClaimError(f"获取 client token 失败: {e}")

    def create_device_code(self) -> Dict[str, Any]:
        """
        创建 Device Code，用于用户在浏览器中授权
        返回: {"device_code": str, "user_code": str, "verification_uri": str, "verification_uri_complete": str, "expires_in": int}
        """
        try:
            # 先获取 client_credentials token
            client_token = self.get_client_token()

            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/deviceAuthorization",
                headers={
                    **EPIC_AUTH_HEADERS,
                    "Authorization": f"bearer {client_token}",
                },
                data={
                    "prompt": "login",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Device Code created: user_code={data.get('user_code')}, expires_in={data.get('expires_in')}")
            return {
                "device_code": data.get("device_code"),
                "user_code": data.get("user_code"),
                "verification_uri": data.get("verification_uri"),
                "verification_uri_complete": data.get("verification_uri_complete"),
                "expires_in": data.get("expires_in", 600),
            }
        except Exception as e:
            logger.error(f"创建 Device Code 失败: {e}")
            raise EpicClaimError(f"创建 Device Code 失败: {e}")

    def poll_device_code(self, device_code: str, timeout: int = 300, interval: int = 5) -> Dict[str, Any]:
        """
        轮询 Device Code 等待用户授权
        返回授权结果（包含 access_token, refresh_token, account_id 等）

        Epic API 错误格式：
        - authorization_pending: {"error": "invalid_grant", "errorCode": "errors.com.epicgames.account.oauth.authorization_pending"}
        - slow_down: {"error": "invalid_grant", "errorCode": "errors.com.epicgames.account.oauth.slow_down"}
        - expired_token: {"error": "invalid_grant", "errorCode": "errors.com.epicgames.account.oauth.authorization_expired"}
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                resp = self.session.post(
                    f"{EPIC_AUTH_API}/account/api/oauth/token",
                    headers={
                        **EPIC_AUTH_HEADERS,
                        "Authorization": f"basic {SWITCH_AUTH_BASIC}",
                    },
                    data={
                        "grant_type": "device_code",
                        "device_code": device_code,
                    },
                )
                data = resp.json()

                if "error" in data:
                    error_code = data.get("errorCode", "")
                    # Epic 使用 errorCode 字段区分不同类型的 invalid_grant 错误
                    if "authorization_pending" in error_code or data["error"] == "authorization_pending":
                        time.sleep(interval)
                        continue
                    elif "slow_down" in error_code or data["error"] == "slow_down":
                        interval = min(interval + 5, 30)
                        time.sleep(interval)
                        continue
                    elif "authorization_expired" in error_code or data["error"] == "expired_token":
                        raise EpicClaimError("授权链接已过期，请重新发送'绑定'获取新链接")
                    else:
                        raise EpicClaimError(f"授权失败: {data.get('error_description', data.get('errorMessage', data.get('error')))}")

                # 授权成功
                return {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                    "account_id": data.get("account_id"),
                    "expires_in": data.get("expires_in", 7200),
                }

            except EpicClaimError:
                raise
            except Exception as e:
                logger.warning(f"轮询 Device Code 异常: {e}")
                time.sleep(interval)

        raise EpicClaimError("授权超时，请在5分钟内完成授权")

    def create_device_auth(self, access_token: str, account_id: str) -> Dict[str, str]:
        """
        使用 access_token 创建 Device Auth 凭证（长期有效）
        返回: {"account_id": str, "device_id": str, "secret": str}
        """
        try:
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/public/account/{account_id}/deviceAuth",
                headers={
                    "Authorization": f"bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "account_id": data.get("accountId", account_id),
                "device_id": data.get("deviceId"),
                "secret": data.get("secret"),
            }
        except Exception as e:
            raise EpicClaimError(f"创建 Device Auth 失败: {e}")

    def login_with_device_auth(self, device_id: str, encrypted_secret: str, account_id: str) -> Dict[str, Any]:
        """
        使用 Device Auth 凭证登录获取 access_token
        使用 fortniteAndroidGameClient（支持 device_auth grant type）
        """
        secret = decrypt_password(encrypted_secret)
        try:
            logger.info(f"Attempting to login with device auth for account {account_id}")
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/token",
                headers={
                    **EPIC_AUTH_HEADERS,
                    "Authorization": f"basic {ANDROID_AUTH_BASIC}",
                },
                data={
                    "grant_type": "device_auth",
                    "account_id": account_id,
                    "device_id": device_id,
                    "secret": secret,
                },
            )
            data = resp.json()

            if "error" in data:
                error_code = data.get("errorCode", "")
                error_msg = data.get("errorMessage", data.get("error_description", data.get("error")))
                logger.error(f"Device Auth login failed: {error_code} - {error_msg}")
                
                if "invalid_client" in error_code or "invalid_grant" in error_code:
                    raise EpicClaimError("Device Auth 已失效，请重新绑定账号")
                raise EpicClaimError(f"Device Auth 登录失败: {error_msg}")

            result = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "account_id": data.get("account_id", account_id),
                "expires_in": data.get("expires_in", 7200),
            }
            
            logger.info(f"Device Auth login successful for account {result.get('account_id')}")
            return result
        except EpicClaimError:
            raise
        except Exception as e:
            logger.exception(f"Device Auth login exception: {e}")
            raise EpicClaimError(f"Device Auth 登录异常: {e}")

    def login_with_refresh_token(self, encrypted_refresh_token: str) -> Dict[str, Any]:
        """
        使用 Refresh Token 登录获取新的 access_token
        使用 fortniteAndroidGameClient
        """
        refresh_token = decrypt_password(encrypted_refresh_token)
        try:
            logger.info("Attempting to login with refresh token")
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/token",
                headers={
                    **EPIC_AUTH_HEADERS,
                    "Authorization": f"basic {ANDROID_AUTH_BASIC}",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "token_type": "eg1",
                },
            )
            data = resp.json()

            if "error" in data:
                error_code = data.get("errorCode", "")
                error_msg = data.get("errorMessage", data.get("error_description", data.get("error")))
                logger.error(f"Refresh Token login failed: {error_code} - {error_msg}")
                
                if "invalid_grant" in error_code or data.get("error") == "invalid_grant":
                    raise EpicClaimError("Refresh Token 已失效，请重新绑定账号")
                raise EpicClaimError(f"Refresh Token 登录失败: {error_msg}")

            result = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "account_id": data.get("account_id"),
                "expires_in": data.get("expires_in", 7200),
            }

            logger.info(f"Refresh Token login successful for account {result.get('account_id')}")

            # 如果返回了新的 refresh_token，需要更新存储
            if data.get("refresh_token"):
                result["new_refresh_token"] = data.get("refresh_token")

            return result

        except EpicClaimError:
            raise
        except Exception as e:
            logger.exception(f"Refresh Token login exception: {e}")
            raise EpicClaimError(f"Refresh Token 登录异常: {e}")

    def _get_exchange_code(self, access_token: str) -> str:
        """通过 access_token 获取 exchange code"""
        try:
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/exchange",
                headers={"Authorization": f"bearer {access_token}"},
            )
            data = resp.json()
            if "errorCode" in data:
                raise EpicClaimError(f"获取 exchange code 失败: {data.get('errorMessage', data.get('errorCode'))}")
            return data.get("code")
        except EpicClaimError:
            raise
        except Exception as e:
            raise EpicClaimError(f"获取 exchange code 失败: {e}")

    def _get_launcher_token(self, exchange_code: str) -> Dict[str, Any]:
        """使用 exchange code 获取 launcher access token（用于购买）"""
        try:
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/token",
                data={
                    "grant_type": "exchange_code",
                    "exchange_code": exchange_code,
                    "scope": "basic profile openid offline_access",
                    "token_type": "eg1",
                },
                headers={
                    **EPIC_AUTH_HEADERS,
                    "Authorization": f"basic {ANDROID_AUTH_BASIC}",
                },
            )
            data = resp.json()
            if "error" in data:
                raise EpicClaimError(f"获取 launcher token 失败: {data.get('errorMessage', data.get('error_description', data.get('error')))}")
            return data
        except EpicClaimError:
            raise
        except Exception as e:
            raise EpicClaimError(f"获取 launcher token 异常: {e}")

    def claim_game(self, offer_id: str, namespace: str,
                   encrypted_refresh_token: str = None,
                   device_id: str = None, encrypted_device_secret: str = None, account_id: str = None,
                   email: str = None, encrypted_password: str = None) -> Dict[str, Any]:
        """
        领取单个免费游戏

        认证优先级：
        1. Refresh Token（推荐）
        2. Device Auth（兼容）
        3. 密码（已弃用，最后回退）

        Returns:
            {"success": bool, "message": str, "game_name": str, "new_refresh_token": str|None}
        """
        new_refresh_token = None
        try:
            # 优先使用 Refresh Token 认证
            if encrypted_refresh_token:
                login_result = self.login_with_refresh_token(encrypted_refresh_token)
                new_refresh_token = login_result.get("new_refresh_token")
            elif device_id and encrypted_device_secret and account_id:
                # 兼容旧的 Device Auth 方式
                login_result = self.login_with_device_auth(device_id, encrypted_device_secret, account_id)
            elif encrypted_password:
                # 回退到密码认证（可能已不可用）
                password = decrypt_password(encrypted_password)
                login_result = self._login_with_password(email or "", password)
            else:
                return {"success": False, "message": "无可用认证方式，请重新绑定账号", "game_name": "", "new_refresh_token": None}

            access_token = login_result["access_token"]
            account_id = login_result["account_id"]
            logger.info(f"Epic 登录成功: account_id={account_id}")

            # 获取 exchange code -> launcher token
            exchange_code = self._get_exchange_code(access_token)
            launcher_token = self._get_launcher_token(exchange_code)
            launcher_access_token = launcher_token["access_token"]

            # 执行购买（领取免费游戏）
            purchase_payload = {
                "operationName": "purchaseGame",
                "variables": {
                    "input": {
                        "offerId": offer_id,
                        "quantity": 1,
                        "totalPrice": 0,
                        "currencyCode": "USD",
                        "purchaseReason": "FREE",
                        "namespace": namespace,
                    }
                },
                "query": PURCHASE_MUTATION,
            }

            purchase_resp = self.session.post(
                EPIC_GRAPHQL_URL,
                json=purchase_payload,
                headers={
                    "Authorization": f"bearer {launcher_access_token}",
                    "Content-Type": "application/json",
                    "User-Agent": EPIC_AUTH_HEADERS["User-Agent"],
                },
            )

            if purchase_resp.status_code == 429:
                return {"success": False, "message": "请求过于频繁，请稍后再试", "game_name": "", "new_refresh_token": new_refresh_token}

            result = purchase_resp.json()

            if "errors" in result:
                error_msg = result["errors"][0].get("message", "未知错误")
                if "already" in error_msg.lower() or "OWNED" in error_msg:
                    return {"success": True, "message": "游戏已拥有", "game_name": "", "new_refresh_token": new_refresh_token}
                return {"success": False, "message": f"领取失败: {error_msg}", "game_name": "", "new_refresh_token": new_refresh_token}

            purchase_data = result.get("data", {}).get("PurchaseGame", {})
            if purchase_data.get("purchaseSuccess"):
                return {"success": True, "message": "领取成功", "game_name": "", "new_refresh_token": new_refresh_token}
            else:
                order_state = purchase_data.get("order", {}).get("state", "")
                if order_state == "COMPLETED":
                    return {"success": True, "message": "领取成功", "game_name": "", "new_refresh_token": new_refresh_token}
                return {"success": False, "message": f"领取状态: {order_state}", "game_name": "", "new_refresh_token": new_refresh_token}

        except EpicClaimError as e:
            logger.error(f"Epic 领取异常: {e}")
            return {"success": False, "message": str(e), "game_name": "", "new_refresh_token": new_refresh_token}
        except Exception as e:
            logger.exception(f"Epic 领取未知异常: {e}")
            return {"success": False, "message": f"系统异常: {e}", "game_name": "", "new_refresh_token": new_refresh_token}

    def _login_with_password(self, email: str, password: str) -> Dict[str, Any]:
        """
        使用邮箱密码登录 Epic（已弃用，仅作回退）
        """
        try:
            login_resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/token",
                data={
                    "grant_type": "password",
                    "username": email,
                    "password": password,
                    "scope": "basic profile openid offline_access",
                },
                headers={
                    **EPIC_AUTH_HEADERS,
                    "Authorization": f"basic {SWITCH_AUTH_BASIC}",
                },
            )
            login_data = login_resp.json()

            if "error" in login_data:
                raise EpicClaimError(f"Epic 密码登录失败: {login_data.get('error_description', login_data.get('error'))}")

            return {
                "access_token": login_data.get("access_token"),
                "refresh_token": login_data.get("refresh_token"),
                "account_id": login_data.get("account_id"),
                "expires_in": login_data.get("expires_in", 7200),
            }

        except EpicClaimError:
            raise
        except Exception as e:
            raise EpicClaimError(f"Epic 登录异常: {e}")


class EpicClaimServiceSingleton:
    """延迟实例化，每次操作创建新 session"""
    def __init__(self):
        self._instance = None

    def claim_game(self, offer_id: str, namespace: str,
                   encrypted_refresh_token: str = None,
                   device_id: str = None, encrypted_device_secret: str = None, account_id: str = None,
                   email: str = None, encrypted_password: str = None) -> Dict[str, Any]:
        service = EpicClaimService()
        try:
            return service.claim_game(
                offer_id=offer_id,
                namespace=namespace,
                encrypted_refresh_token=encrypted_refresh_token,
                device_id=device_id,
                encrypted_device_secret=encrypted_device_secret,
                account_id=account_id,
                email=email,
                encrypted_password=encrypted_password,
            )
        finally:
            service.session.close()

    def create_device_code(self) -> Dict[str, Any]:
        service = EpicClaimService()
        try:
            return service.create_device_code()
        finally:
            service.session.close()

    def poll_device_code(self, device_code: str, timeout: int = 300, interval: int = 5) -> Dict[str, Any]:
        service = EpicClaimService()
        try:
            return service.poll_device_code(device_code, timeout, interval)
        finally:
            service.session.close()

    def create_device_auth(self, access_token: str, account_id: str) -> Dict[str, str]:
        service = EpicClaimService()
        try:
            return service.create_device_auth(access_token, account_id)
        finally:
            service.session.close()


epic_claim_service = EpicClaimServiceSingleton()
