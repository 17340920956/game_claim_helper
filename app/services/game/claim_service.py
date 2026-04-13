"""
Epic Games 自动领取服务
通过 Device Code + Device Auth 认证，使用 Playwright 浏览器自动化领取免费游戏

认证流程：
1. 用 fortniteNewSwitchGameClient 获取 client_credentials token
2. 用该 token 创建 deviceAuthorization（Device Code）
3. 用户在浏览器中授权
4. 用 device_code 获取 access_token + refresh_token
5. 用 access_token 创建 Device Auth 凭证（长期有效）
6. 后续领取用 Device Auth 登录获取 access_token
7. 使用 Playwright 浏览器自动化领取游戏（点击 GET 按钮）

领取流程：
- 用 Refresh Token 登录获取 access_token 和 sid cookie
- 启动 Playwright Chromium 浏览器
- 注入 Epic 登录态（cookie）
- 访问游戏购买页面
- 点击「GET」/「领取」按钮完成购买
"""
import requests
import json
import time
import asyncio
import nest_asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.core.logger import logger

# 允许在已有事件循环中运行新的异步代码
nest_asyncio.apply()


# Epic 登录相关常量
EPIC_AUTH_API = "https://account-public-service-prod.ol.epicgames.com"
EPIC_ORDER_API = "https://store-site-backend-static.ak.epicgames.com"
EPIC_STORE_URL = "https://www.epicgames.com"
EPIC_PURCHASE_URL = "https://www.epicgames.com/purchase"

# fortniteNewSwitchGameClient 凭证（支持 client_credentials + device_code grant type）
SWITCH_AUTH_BASIC = "OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"

# Epic 登录 Headers
EPIC_AUTH_HEADERS = {
    "User-Agent": "Fortnite/++Fortnite+Release-31.00-CL-33594855 Android/12",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*",
}


class EpicClaimError(Exception):
    """Epic 领取异常"""
    pass


class EpicClaimService:
    """Epic 免费游戏自动领取服务 - Playwright 浏览器自动化"""

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
        使用 fortniteNewSwitchGameClient（支持 device_auth grant type）
        """
        from app.core.crypto import decrypt_password
        secret = decrypt_password(encrypted_secret)
        try:
            logger.info(f"Attempting to login with device auth for account {account_id}")
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/token",
                headers={
                    **EPIC_AUTH_HEADERS,
                    "Authorization": f"basic {SWITCH_AUTH_BASIC}",
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
        使用 fortniteNewSwitchGameClient
        """
        from app.core.crypto import decrypt_password
        refresh_token = decrypt_password(encrypted_refresh_token)
        try:
            logger.info("Attempting to login with refresh token")
            resp = self.session.post(
                f"{EPIC_AUTH_API}/account/api/oauth/token",
                headers={
                    **EPIC_AUTH_HEADERS,
                    "Authorization": f"basic {SWITCH_AUTH_BASIC}",
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

            if data.get("refresh_token"):
                result["new_refresh_token"] = data.get("refresh_token")

            return result

        except EpicClaimError:
            raise
        except Exception as e:
            logger.exception(f"Refresh Token login exception: {e}")
            raise EpicClaimError(f"Refresh Token 登录异常: {e}")

    def _get_epic_cookies(self, access_token: str) -> List[Dict]:
        """
        通过 Epic OAuth API 获取登录后的 cookies（sid 等）
        用于注入到 Playwright 浏览器中实现已登录状态
        """
        from app.core.crypto import decrypt_password
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Origin": "https://www.epicgames.com",
            "Referer": "https://www.epicgames.com/",
        })

        cookies_list = []

        # 1. 访问 epicgames.com 获取初始 cookies
        try:
            init_resp = session.get("https://www.epicgames.com/", timeout=15)
            for cookie in session.cookies:
                cookies_list.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                })
            logger.info(f"获取初始 cookies: {[c['name'] for c in cookies_list]}")
        except Exception as e:
            logger.warning(f"获取初始 cookies 失败: {e}")

        # 2. 通过 OAuth exchange 获取 EPIC_BEARER_TOKEN（这是关键 cookie）
        try:
            exchange_resp = session.get(
                f"{EPIC_AUTH_API}/account/api/oauth/exchange",
                headers={"Authorization": f"bearer {access_token}"},
                timeout=15,
            )
            exchange_data = exchange_resp.json()
            if "errorCode" not in exchange_data:
                bearer_token = exchange_data.get("code", "")
                
                # 3. 用 bearer_token 设置 EPIC_BEARER_TOKEN cookie
                cookies_list.append({
                    "name": "EPIC_BEARER_TOKEN",
                    "value": bearer_token,
                    "domain": ".epicgames.com",
                    "path": "/",
                })
                logger.info(f"获取 EPIC_BEARER_TOKEN 成功: {bearer_token[:20]}...")
            else:
                logger.warning(f"OAuth exchange 失败: {exchange_data.get('errorCode')}")
        except Exception as e:
            logger.warning(f"获取 EPIC_BEARER_TOKEN 失败: {e}")

        session.close()
        return cookies_list

    async def _claim_with_playwright(self, offer_id: str, namespace: str, game_url: str, 
                                      access_token: str, account_id: str) -> Dict[str, Any]:
        """
        使用 Playwright 浏览器自动化领取游戏
        核心逻辑：打开游戏页面 → 检测是否已拥有 → 点击 GET → 确认领取
        """
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

        browser = None
        page = None
        try:
            pw = await async_playwright().start()
            
            # 启动 Chromium（headless 模式，无头服务器环境）
            # 尝试查找 Chromium 可执行文件
            import os
            chromium_paths = [
                "/root/.cache/ms-playwright/chromium-1148/chrome-linux/chrome",
                "/root/.cache/ms-playwright/chromium-1148/chrome-linux/chromium",
            ]
            executable_path = None
            for path in chromium_paths:
                if os.path.exists(path):
                    executable_path = path
                    logger.info(f"使用 Chromium 可执行文件: {executable_path}")
                    break
            
            # 如果找不到 chromium，尝试使用 chrome
            if not executable_path:
                chrome_paths = [
                    "/usr/bin/google-chrome",
                    "/usr/bin/chromium",
                    "/usr/bin/chromium-browser",
                ]
                for path in chrome_paths:
                    if os.path.exists(path):
                        executable_path = path
                        logger.info(f"使用系统 Chrome: {executable_path}")
                        break
            
            launch_options = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    "--no-zygote",
                    "--disable-software-rasterizer",
                    "--window-size=1280,800",
                ]
            }
            
            if executable_path:
                launch_options["executable_path"] = executable_path
                logger.info(f"启动浏览器，executable_path={executable_path}")
            else:
                logger.warning("未找到浏览器可执行文件，尝试使用默认路径")
            
            # 使用 browser_type 方式启动，避免 Playwright 自动查找 headless_shell
            browser_type = pw.chromium
            browser = await browser_type.launch(**launch_options)

            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
            )

            page = await context.new_page()

            # 注入登录 cookies
            cookies = self._get_epic_cookies(access_token)
            if cookies:
                await context.add_cookies(cookies)
                logger.info(f"已注入 {len(cookies)} 个 cookies 到浏览器")

            # 构建购买 URL
            purchase_url = f"https://www.epicgames.com/en-US/p/{game_url}" if game_url else None
            if not purchase_url or not game_url:
                purchase_url = f"https://store.epicgames.com/en-US/p/{offer_id}"

            logger.info(f"打开游戏页面: {purchase_url}")

            # 访问游戏页面
            await page.goto(purchase_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            current_url = page.url
            page_content = await page.content()
            logger.info(f"当前页面 URL: {current_url}")
            logger.info(f"页面标题: {await page.title()}")

            # 检查是否需要登录（被重定向到登录页）
            if "id.epicgames.com" in current_url or "accounts.epicgames.com" in current_url:
                logger.warning("页面跳转到登录页，尝试通过 cookie 登录...")
                
                # 尝试直接访问 Epic Store 主页检查登录状态
                await page.goto("https://www.epicgames.com/", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)
                
                # 如果仍然在登录页，说明 cookie 无效
                if "id.epicgames.com" in page.url or "accounts.epicgames.com" in page.url:
                    return {
                        "success": False,
                        "message": "Epic 登录态已过期，请重新发送'绑定'更新凭证",
                        "game_name": "",
                    }

            # 回到游戏页面
            await page.goto(purchase_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # 检查是否已经拥有该游戏
            page_text = await page.text_content("body") or ""
            if "owned" in page_text.lower() or "already own" in page_text.lower() or "已在库中" in page_text:
                logger.info("检测到游戏已拥有")
                return {"success": True, "message": "游戏已拥有", "game_name": ""}

            # 查找并点击「GET」或「领取」按钮
            get_button_selectors = [
                'button:has-text("GET")',
                'button:has-text("Get")',
                'button:has-text("领取")',
                'button:has-text("Claim")',
                '[data-testid="purchase-cta-button"]',
                '.purchase-btn',
                'a[href*="purchase"][href*="offerId"]',
                'button.cta-btn',
                '#purchase button',
            ]

            clicked_get = False
            for selector in get_button_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        btn_text = await btn.text_content()
                        logger.info(f"找到按钮 [{selector}]: {btn_text}")
                        await btn.click()
                        clicked_get = True
                        break
                except Exception as e:
                    logger.debug(f"选择器 [{selector}] 未找到或点击失败: {e}")
                    continue

            if not clicked_get:
                # 截图辅助调试
                screenshot_path = f"/tmp/epic_claim_{int(time.time())}.png"
                try:
                    await page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"未找到 GET 按钮，截图保存至: {screenshot_path}")
                except Exception:
                    pass
                
                # 尝试查找页面上所有按钮的文本
                buttons_info = []
                try:
                    buttons = await page.query_selector_all("button")
                    for b in buttons:
                        try:
                            text = await b.text_content()
                            visible = await b.is_visible()
                            if visible and text:
                                buttons_info.append(text.strip())
                        except Exception:
                            pass
                    logger.info(f"页面上可见的按钮: {buttons_info}")
                except Exception as e:
                    logger.debug(f"枚举按钮失败: {e}")

                return {
                    "success": False,
                    "message": "未找到领取按钮，可能需要先在 Epic 客户端登录一次",
                    "game_name": "",
                }

            logger.info("已点击 GET 按钮，等待弹窗...")
            await page.wait_for_timeout(3000)

            # 在弹窗中点击「Place Order」或「确认」按钮
            place_order_selectors = [
                'button:has-text("Place Order")',
                'button:has-text("place order")',
                'button:has-text("Confirm")',
                'button:has-text("确认")',
                'button:has-text("Yes")',
                'button:has-text("是")',
                '[data-testid="confirm-purchase-btn"]',
                '.purchase-confirm-btn',
            ]

            clicked_confirm = False
            for selector in place_order_selectors:
                try:
                    confirm_btn = await page.query_selector(selector)
                    if confirm_btn and await confirm_btn.is_visible():
                        btn_text = await confirm_btn.text_content()
                        logger.info(f"找到确认按钮 [{selector}]: {btn_text}")
                        await confirm_btn.click()
                        clicked_confirm = True
                        break
                except Exception as e:
                    logger.debug(f"确认选择器 [{selector}] 失败: {e}")
                    continue

            if clicked_confirm:
                logger.info("已点击确认按钮，等待订单处理...")
                await page.wait_for_timeout(5000)

            # 最终验证：检查是否成功
            final_text = await page.text_content("body") or ""
            final_url = page.url
            
            success_indicators = ["owned", "thank you", "success", "purchased", "claimed", "已拥有", "成功", "感谢"]
            failure_indicators = ["error", "failed", "unable", "unavailable", "not available"]

            for indicator in success_indicators:
                if indicator.lower() in final_text.lower() or indicator.lower() in final_url.lower():
                    logger.info(f"领取成功! 检测到: {indicator}")
                    return {"success": True, "message": "领取成功!", "game_name": ""}

            for indicator in failure_indicators:
                if indicator.lower() in final_text.lower():
                    logger.warning(f"可能失败: 检测到 {indicator}")
                    
            # 默认认为成功（如果没报错的话）
            logger.info("领取流程执行完毕")
            return {"success": True, "message": "领取请求已提交", "game_name": ""}

        except Exception as e:
            logger.exception(f"Playwright 浏览器自动化异常: {e}")
            return {"success": False, "message": f"浏览器操作异常: {str(e)}", "game_name": ""}
        
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

    def claim_game(self, offer_id: str, namespace: str,
                   encrypted_refresh_token: str = None,
                   device_id: str = None, encrypted_device_secret: str = None, account_id: str = None,
                   email: str = None, encrypted_password: str = None,
                   game_slug: str = None, game_url: str = None) -> Dict[str, Any]:
        """
        领取单个免费游戏 - 使用 Playwright 浏览器自动化

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
                login_result = self.login_with_device_auth(device_id, encrypted_device_secret, account_id)
            elif encrypted_password:
                from app.core.crypto import decrypt_password
                password = decrypt_password(encrypted_password)
                login_result = self._login_with_password(email or "", password)
            else:
                return {"success": False, "message": "无可用认证方式，请重新绑定账号", "game_name": "", "new_refresh_token": None}

            access_token = login_result["access_token"]
            acc_id = login_result["account_id"]
            logger.info(f"Epic 登录成功: account_id={acc_id}")

            # 使用 Playwright 浏览器自动化领取
            logger.info(f"开始使用 Playwright 领取游戏: offer_id={offer_id}, namespace={namespace}")

            # 运行异步 Playwright 操作 - 使用 nest_asyncio 兼容已有事件循环
            import nest_asyncio
            nest_asyncio.apply()
            
            result = asyncio.get_event_loop().run_until_complete(
                self._claim_with_playwright(
                    offer_id=offer_id,
                    namespace=namespace,
                    game_url=game_slug or game_url or "",
                    access_token=access_token,
                    account_id=acc_id,
                )
            )

            result["new_refresh_token"] = new_refresh_token
            return result

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
                   email: str = None, encrypted_password: str = None,
                   game_slug: str = None, game_url: str = None) -> Dict[str, Any]:
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
                game_slug=game_slug,
                game_url=game_url,
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
