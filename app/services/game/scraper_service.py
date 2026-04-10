import requests
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from app.core.config import get_settings
from app.core.logger import logger
from app.db.redis import redis_client

settings = get_settings()

class EpicScraper:
    """
    Epic Games Store 免费游戏爬虫
    负责从 Epic 官方接口获取每周免费游戏信息
    """
    def __init__(self):
        self.base_url = settings.EPIC_FREE_GAMES_URL
        self.api_url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        解析日期字符串，转换为 UTC aware datetime
        Epic API 返回的是 UTC 时间 (ISO 8601)
        """
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # 确保返回 UTC 时区的 datetime
            if dt.tzinfo is None:
                from datetime import timezone
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            return None
    
    def _is_current_free(self, promotion: Dict[str, Any]) -> bool:
        """
        判断是否为当前免费游戏
        检查 promotionalOffers 中 discountPercentage 是否为 0
        同时检查 upcomingPromotionalOffers 中已开始的活动（start_time 已过）
        """
        if not promotion:
            return False
        
        now = datetime.now().astimezone()
        
        promotional_offers = promotion.get("promotionalOffers", [])
        for offer_container in promotional_offers:
            for offer in offer_container.get("promotionalOffers", []):
                if offer.get("discountSetting", {}).get("discountPercentage", 0) == 0:
                    return True
        
        # 检查 upcomingPromotionalOffers 中已开始的活动
        # Epic API 有时会将当前进行中的活动放在 upcomingPromotionalOffers 中
        upcoming_offers = promotion.get("upcomingPromotionalOffers", [])
        for offer_container in upcoming_offers:
            for offer in offer_container.get("promotionalOffers", []):
                if offer.get("discountSetting", {}).get("discountPercentage", 0) == 0:
                    start_date = self._parse_date(offer.get("startDate"))
                    if start_date and start_date <= now:
                        return True
        return False
    
    def _is_upcoming_free(self, promotion: Dict[str, Any]) -> bool:
        """
        判断是否为即将到来的免费游戏（尚未开始）
        检查 upcomingPromotionalOffers 中的折扣信息，且 start_time 在未来
        """
        if not promotion:
            return False
        
        now = datetime.now().astimezone()
        
        upcoming_offers = promotion.get("upcomingPromotionalOffers", [])
        for offer_container in upcoming_offers:
            for offer in offer_container.get("promotionalOffers", []):
                if offer.get("discountSetting", {}).get("discountPercentage", 0) == 0:
                    start_date = self._parse_date(offer.get("startDate"))
                    # 只有尚未开始的活动才归为"即将免费"
                    if start_date and start_date > now:
                        return True
        return False
    
    def _parse_game(self, game_data: Dict[str, Any], is_upcoming: bool = False) -> Dict[str, Any]:
        """
        解析单个游戏数据，提取标题、Slug、图片等关键信息
        """
        title = game_data.get("title", "Unknown")
        
        # 尝试获取 slug 逻辑保持不变...
        custom_attributes = game_data.get("customAttributes", [])
        page_slug = None
        offer_id = game_data.get("id", "")
        namespace = game_data.get("catalogNs", {}).get("mappings", [{}])[0].get("namespace", "") or game_data.get("namespace", "")
        for attr in custom_attributes:
            if attr.get("key") == "com.epicgames.app.productSlug":
                page_slug = attr.get("value")
                break
        
        if not page_slug:
            for mapping in game_data.get("offerMappings", []):
                if mapping.get("pageSlug"):
                    page_slug = mapping.get("pageSlug")
                    break
                    
        if not page_slug:
            mappings = game_data.get("catalogNs", {}).get("mappings", [])
            for mapping in mappings:
                if mapping.get("pageSlug"):
                    page_slug = mapping.get("pageSlug")
                    break

        if not page_slug:
            page_slug = game_data.get("productSlug") or game_data.get("urlSlug")
        
        if not page_slug and title:
            page_slug = title.lower().replace(" ", "-")
            
        if page_slug and "/" in page_slug:
             if page_slug.endswith("/home"):
                 page_slug = page_slug.replace("/home", "")
        
        url = f"https://store.epicgames.com/zh-CN/p/{page_slug}" if page_slug else ""
        
        image_url = ""
        for image in game_data.get("keyImages", []):
            if image.get("type") == "OfferImageTall":
                image_url = image.get("url", "")
                break
        
        if not image_url:
            for image in game_data.get("keyImages", []):
                if image.get("type") in ["Thumbnail", "OfferImageWide", "DieselStoreFrontWide", "VaultClosed"]:
                    image_url = image.get("url", "")
                    break
        
        if not image_url and game_data.get("keyImages"):
             image_url = game_data.get("keyImages")[0].get("url", "")
        
        promotion = game_data.get("promotions", {})
        
        start_date = None
        end_date = None
        
        # 对于即将免费的游戏，优先使用 upcomingPromotionalOffers 的时间
        if is_upcoming:
            upcoming_offers = promotion.get("upcomingPromotionalOffers", [])
            for offer_container in upcoming_offers:
                for offer in offer_container.get("promotionalOffers", []):
                    if offer.get("discountSetting", {}).get("discountPercentage", 0) == 0:
                        start_date = self._parse_date(offer.get("startDate"))
                        end_date = self._parse_date(offer.get("endDate"))
                        break
                if start_date:
                    break
        
        # 如果没有从upcoming获取到时间，从 promotionalOffers 获取
        if not start_date:
            promotional_offers = promotion.get("promotionalOffers", [])
            for offer_container in promotional_offers:
                for offer in offer_container.get("promotionalOffers", []):
                    start_date = self._parse_date(offer.get("startDate"))
                    end_date = self._parse_date(offer.get("endDate"))
                    break
                if start_date:
                    break
        
        if not start_date:
            upcoming_offers = promotion.get("upcomingPromotionalOffers", [])
            for offer_container in upcoming_offers:
                for offer in offer_container.get("promotionalOffers", []):
                    start_date = self._parse_date(offer.get("startDate"))
                    end_date = self._parse_date(offer.get("endDate"))
                    break
                if start_date:
                    break
        
        # 序列化datetime为ISO格式字符串
        return {
            "name": title,
            "link": url,
            "start_time": start_date.isoformat() if start_date else None,
            "end_time": end_date.isoformat() if end_date else None,
            "image_url": image_url,
            "offer_id": offer_id,
            "namespace": namespace,
            "note": page_slug
        }
    
    def fetch_free_games(self) -> Dict[str, List[Dict[str, Any]]]:
        current_games = []
        upcoming_games = []
        
        try:
            params = {
                "locale": "zh-CN",
                "country": "CN",
                "allowCountries": "CN",
            }
            
            response = requests.get(
                self.api_url, 
                headers=self.headers, 
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
            
            for game in elements:
                promotions = game.get("promotions")
                
                if self._is_current_free(promotions):
                    current_games.append(self._parse_game(game, is_upcoming=False))
                elif self._is_upcoming_free(promotions):
                    upcoming_games.append(self._parse_game(game, is_upcoming=True))
            
        except requests.RequestException as e:
            logger.error(f"API请求失败: {e}")
            return {"current": [], "upcoming": []}
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"解析数据失败: {e}")
            return {"current": [], "upcoming": []}
        
        return {
            "current": current_games,
            "upcoming": upcoming_games
        }

scraper = EpicScraper()

def fetch_and_store_games():
    """
    协调函数：调用爬虫获取数据，并存储到 Redis
    """
    logger.info("开始爬取Epic免费游戏...")
    games = scraper.fetch_free_games()
    
    try:
        # 存储当前免费游戏到Redis
        redis_client.set_current_week_games(games["current"])
        logger.info(f"存储当前免费游戏 {len(games['current'])} 款到Redis")
        
        # 存储下周预告游戏到Redis
        redis_client.set_next_week_games(games["upcoming"])
        logger.info(f"存储下周预告游戏 {len(games['upcoming'])} 款到Redis")
        
    except Exception as e:
        logger.error(f"存储游戏数据到Redis失败: {e}")
    
    return games

if __name__ == "__main__":
    games = fetch_and_store_games()
    print(json.dumps(games, ensure_ascii=False, indent=2))
