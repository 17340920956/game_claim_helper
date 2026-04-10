"""
Epic Games 自动领取服务
通过 Epic GraphQL API 登录并领取免费游戏
"""
import requests
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.core.logger import logger
from app.core.crypto import decrypt_password


# Epic 登录相关常量
EPIC_AUTH_API = "https://account-public-service-prod03.ak.epicgames.com"
EPIC_LAUNCHER_API = "https://launcher-public-service-prod08.ol.epicgames.com"
EPIC_GRAPHQL_URL = "https://graphql.epicgames.com/graphql"
EPIC_ORDER_API = "https://store-site-backend-static.ak.epicgames.com"

# launcherAppClient2 凭证
EPIC_CLIENT_ID = "34a02cf8f4414e29b15921876da36f9a"
EPIC_CLIENT_SECRET = "daafbccc737745039dffe53d94fc76cf"
EPIC_AUTH_BASIC = "MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzZmOWE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc2Y2Y="

# Epic 登录 Headers
EPIC_AUTH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) EpicGamesLauncher/13.0.0-14995143+++Portal+Release-Live Chrome/108.0.5359.215 Safari/537.36",
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

    def _login_with_credentials(self, email: str, password: str) -> Dict[str, Any]:
        """
        使用邮箱密码登录 Epic，获取授权码
        返回: {"authorizationCode": str, "accountId": str}
        """
        # Step 1: 初始化登录会话
        try:
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/token",
                headers={
                    **EPIC_AUTH_HEADERS,
                    "Authorization": f"basic {EPIC_AUTH_BASIC}",
                },
                data={
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
        except Exception as e:
            raise EpicClaimError(f"初始化 Epic 会话失败: {e}")

        # Step 2: 使用邮箱密码获取 authorization code
        try:
            login_resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/token",
                data={
                    "grant_type": "password",
                    "username": email,
                    "password": password,
                    "scope": "basic profile openid offline_access",
                },
            )
            login_data = login_resp.json()

            if "error" in login_data:
                raise EpicClaimError(f"Epic 登录失败: {login_data.get('error_description', login_data.get('error'))}")

            # 获取 account_id
            # 用 access_token 获取用户信息
            access_token = login_data.get("access_token")
            account_id = login_data.get("account_id")

            if not account_id:
                user_info_resp = self.session.get(
                    f"{EPIC_AUTH_API}/account/api/oauth/accountInfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                user_info = user_info_resp.json()
                account_id = user_info[0].get("accountId") if user_info else None

            return {
                "access_token": access_token,
                "refresh_token": login_data.get("refresh_token"),
                "account_id": account_id,
                "expires_in": login_data.get("expires_in", 7200),
            }

        except EpicClaimError:
            raise
        except Exception as e:
            raise EpicClaimError(f"Epic 登录异常: {e}")

    def _get_exchange_code(self, access_token: str) -> str:
        """通过 access_token 获取 exchange code"""
        try:
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/exchange",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("code")
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
                    "Authorization": f"basic {EPIC_AUTH_BASIC}",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise EpicClaimError(f"获取 launcher token 失败: {data.get('error_description')}")
            return data
        except EpicClaimError:
            raise
        except Exception as e:
            raise EpicClaimError(f"获取 launcher token 异常: {e}")

    def _get_user_entitlements(self, access_token: str, account_id: str) -> List[str]:
        """获取用户已拥有的游戏 entitlements"""
        try:
            resp = self.session.get(
                f"{EPIC_LAUNCHER_API}/launcher/api/public/entitlements/{account_id}?includeUsage=false",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return [e.get("entitlementName", "") for e in data]
        except Exception as e:
            logger.warning(f"获取用户 entitlements 失败: {e}")
            return []

    def claim_game(self, email: str, encrypted_password: str, offer_id: str, namespace: str) -> Dict[str, Any]:
        """
        领取单个免费游戏

        Args:
            email: Epic 账号邮箱
            encrypted_password: 加密的 Epic 密码
            offer_id: 游戏 offer ID (如 catalogNs/mappings 中的 offerId)
            namespace: 游戏命名空间

        Returns:
            {"success": bool, "message": str, "game_name": str}
        """
        password = decrypt_password(encrypted_password)

        try:
            # 1. 登录获取 access_token
            login_result = self._login_with_credentials(email, password)
            access_token = login_result["access_token"]
            account_id = login_result["account_id"]
            logger.info(f"Epic 登录成功: account_id={account_id}")

            # 2. 获取 exchange code -> launcher token
            exchange_code = self._get_exchange_code(access_token)
            launcher_token = self._get_launcher_token(exchange_code)
            launcher_access_token = launcher_token["access_token"]

            # 3. 执行购买（领取免费游戏）
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
                    "Authorization": f"Bearer {launcher_access_token}",
                    "Content-Type": "application/json",
                    "User-Agent": EPIC_AUTH_HEADERS["User-Agent"],
                },
            )

            if purchase_resp.status_code == 429:
                return {"success": False, "message": "请求过于频繁，请稍后再试", "game_name": ""}

            result = purchase_resp.json()

            if "errors" in result:
                error_msg = result["errors"][0].get("message", "未知错误")
                if "already" in error_msg.lower() or "OWNED" in error_msg:
                    return {"success": True, "message": "游戏已拥有", "game_name": ""}
                return {"success": False, "message": f"领取失败: {error_msg}", "game_name": ""}

            purchase_data = result.get("data", {}).get("PurchaseGame", {})
            if purchase_data.get("purchaseSuccess"):
                return {"success": True, "message": "领取成功", "game_name": ""}
            else:
                order_state = purchase_data.get("order", {}).get("state", "")
                if order_state == "COMPLETED":
                    return {"success": True, "message": "领取成功", "game_name": ""}
                return {"success": False, "message": f"领取状态: {order_state}", "game_name": ""}

        except EpicClaimError as e:
            logger.error(f"Epic 领取异常: {e}")
            return {"success": False, "message": str(e), "game_name": ""}
        except Exception as e:
            logger.exception(f"Epic 领取未知异常: {e}")
            return {"success": False, "message": f"系统异常: {e}", "game_name": ""}


class EpicClaimServiceSingleton:
    """延迟实例化，每次 claim_game 创建新 session"""
    def __init__(self):
        self._instance = None

    def claim_game(self, email: str, encrypted_password: str, offer_id: str, namespace: str) -> Dict[str, Any]:
        # 每次领取创建新实例，避免 session 复用问题
        service = EpicClaimService()
        try:
            return service.claim_game(email, encrypted_password, offer_id, namespace)
        finally:
            service.session.close()


epic_claim_service = EpicClaimServiceSingleton()
