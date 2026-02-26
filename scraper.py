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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
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
        slug = game_data.get("productSlug", game_data.get("urlSlug", title.lower().replace(" ", "-")))
        if slug:
            slug = slug.split("/")[0]
        
        url = f"https://store.epicgames.com/en-US/p/{slug}" if slug else ""
        
        image_url = ""
        for image in game_data.get("keyImages", []):
            if image.get("type") in ["Thumbnail", "OfferImageWide", "DieselStoreFrontWide"]:
                image_url = image.get("url", "")
                break
        
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
            "slug": slug,
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
                "locale": "en-US",
                "country": "US",
                "allowCountries": "US",
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
    from redis_client import redis_client
    
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
