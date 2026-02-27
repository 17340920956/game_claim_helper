import requests
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from config import get_settings

settings = get_settings()

class EpicScraper:
    def __init__(self):
        self.base_url = settings.EPIC_FREE_GAMES_URL
        self.api_url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            return date_str
    
    def _is_current_free(self, promotion: Dict[str, Any]) -> bool:
        if not promotion:
            return False
        
        promotional_offers = promotion.get("promotionalOffers", [])
        for offer_container in promotional_offers:
            for offer in offer_container.get("promotionalOffers", []):
                if offer.get("discountSetting", {}).get("discountPercentage", 0) == 0:
                    return True
        return False
    
    def _is_upcoming_free(self, promotion: Dict[str, Any]) -> bool:
        if not promotion:
            return False
        
        upcoming_offers = promotion.get("upcomingPromotionalOffers", [])
        for offer_container in upcoming_offers:
            for offer in offer_container.get("promotionalOffers", []):
                if offer.get("discountSetting", {}).get("discountPercentage", 0) == 0:
                    return True
        return False
    
    def _parse_game(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        title = game_data.get("title", "Unknown")
        # 修复逻辑：优先使用 productSlug，如果包含 '/' 则不分割，因为有些 slug 可能是带层级的
        # 但 Epic URL 通常是 p/slug，所以我们尽量获取纯净的 slug
        
        # 尝试获取自定义属性中的 slug
        custom_attributes = game_data.get("customAttributes", [])
        page_slug = None
        for attr in custom_attributes:
            if attr.get("key") == "com.epicgames.app.productSlug":
                page_slug = attr.get("value")
                break
        
        if not page_slug:
            # 尝试从 mapping 或 offerMappings 中获取
            for mapping in game_data.get("offerMappings", []):
                if mapping.get("pageSlug"):
                    page_slug = mapping.get("pageSlug")
                    break
                    
        if not page_slug:
            # 尝试从 catalogNs.mappings 中获取 (如果有这种结构)
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
             # 有些特殊的 slug 可能包含路径，保留或者处理视情况而定
             # 通常只要第一部分
             if page_slug.endswith("/home"):
                 page_slug = page_slug.replace("/home", "")
        
        url = f"https://store.epicgames.com/zh-CN/p/{page_slug}" if page_slug else ""
        
        image_url = ""
        # 优先寻找 Tall 类型的图片（竖图），其次是 Thumbnail
        for image in game_data.get("keyImages", []):
            if image.get("type") == "OfferImageTall":
                image_url = image.get("url", "")
                break
        
        if not image_url:
            for image in game_data.get("keyImages", []):
                # 增加更多图片类型匹配
                if image.get("type") in ["Thumbnail", "OfferImageWide", "DieselStoreFrontWide", "VaultClosed"]:
                    image_url = image.get("url", "")
                    break
        
        # 如果还是没有图片，尝试任意一张
        if not image_url and game_data.get("keyImages"):
             image_url = game_data.get("keyImages")[0].get("url", "")
        
        promotion = game_data.get("promotions", {})
        
        start_date = None
        end_date = None
        
        promotional_offers = promotion.get("promotionalOffers", [])
        for offer_container in promotional_offers:
            for offer in offer_container.get("promotionalOffers", []):
                start_date = self._parse_date(offer.get("startDate"))
                end_date = self._parse_date(offer.get("endDate"))
                break
        
        if not start_date:
            upcoming_offers = promotion.get("upcomingPromotionalOffers", [])
            for offer_container in upcoming_offers:
                for offer in offer_container.get("promotionalOffers", []):
                    start_date = self._parse_date(offer.get("startDate"))
                    end_date = self._parse_date(offer.get("endDate"))
                    break
        
        return {
            "title": title,
            "slug": page_slug,
            "url": url,
            "start_date": start_date,
            "end_date": end_date,
            "thumbnail": image_url,
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
                    current_games.append(self._parse_game(game))
                elif self._is_upcoming_free(promotions):
                    upcoming_games.append(self._parse_game(game))
            
        except requests.RequestException as e:
            print(f"API请求失败: {e}")
            return self._fallback_scrape()
        except (KeyError, json.JSONDecodeError) as e:
            print(f"解析数据失败: {e}")
            return {"current": [], "upcoming": []}
        
        return {
            "current": current_games,
            "upcoming": upcoming_games
        }
    
    def _fallback_scrape(self) -> Dict[str, List[Dict[str, Any]]]:
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            
            script_tags = soup.find_all("script")
            for script in script_tags:
                if script.string and "freeGamesPromotions" in script.string:
                    match = re.search(r'{"props".*?}', script.string)
                    if match:
                        data = json.loads(match.group())
                        return {"current": [], "upcoming": []}
            
        except Exception as e:
            print(f"备用爬取失败: {e}")
        
        return {"current": [], "upcoming": []}


scraper = EpicScraper()


def fetch_and_store_games():
    from db.redis import redis_client
    
    print("开始爬取Epic免费游戏...")
    games = scraper.fetch_free_games()
    
    if games["current"]:
        redis_client.set_current_week_games(games["current"])
        print(f"本周免费游戏已更新: {len(games['current'])} 款")
    
    if games["upcoming"]:
        redis_client.set_next_week_games(games["upcoming"])
        print(f"下周预告游戏已更新: {len(games['upcoming'])} 款")
    
    return games


if __name__ == "__main__":
    games = fetch_and_store_games()
    print(json.dumps(games, ensure_ascii=False, indent=2))
