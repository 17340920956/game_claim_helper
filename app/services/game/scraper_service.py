import requests
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from app.core.config import get_settings
from app.core.logger import logger
from app.db.session import SessionLocal
from app.repositories.game.game_repository import GameRepository
from app.schemas.base import FreeGameCreate

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
        解析日期字符串，转换为本地时间格式
        Epic API 返回的是 UTC 时间 (ISO 8601)
        """
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt
        except (ValueError, AttributeError):
            return None
    
    def _is_current_free(self, promotion: Dict[str, Any]) -> bool:
        """
        判断是否为当前免费游戏
        检查 discountPercentage 是否为 0
        """
        if not promotion:
            return False
        
        promotional_offers = promotion.get("promotionalOffers", [])
        for offer_container in promotional_offers:
            for offer in offer_container.get("promotionalOffers", []):
                if offer.get("discountSetting", {}).get("discountPercentage", 0) == 0:
                    return True
        return False
    
    def _is_upcoming_free(self, promotion: Dict[str, Any]) -> bool:
        """
        判断是否为即将到来的免费游戏
        检查 upcomingPromotionalOffers 中的折扣信息
        """
        if not promotion:
            return False
        
        upcoming_offers = promotion.get("upcomingPromotionalOffers", [])
        for offer_container in upcoming_offers:
            for offer in offer_container.get("promotionalOffers", []):
                if offer.get("discountSetting", {}).get("discountPercentage", 0) == 0:
                    return True
        return False
    
    def _parse_game(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析单个游戏数据，提取标题、Slug、图片等关键信息
        """
        title = game_data.get("title", "Unknown")
        
        # 尝试获取 slug 逻辑保持不变...
        custom_attributes = game_data.get("customAttributes", [])
        page_slug = None
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
            "name": title,
            "link": url,
            "start_time": start_date,
            "end_time": end_date,
            "image_url": image_url,
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
                    current_games.append(self._parse_game(game))
                elif self._is_upcoming_free(promotions):
                    upcoming_games.append(self._parse_game(game))
            
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
    协调函数：调用爬虫获取数据，并存储到 DB
    """
    logger.info("开始爬取Epic免费游戏...")
    games = scraper.fetch_free_games()
    
    db = SessionLocal()
    repo = GameRepository(db)
    
    stored_games = []
    
    try:
        # 处理当前免费游戏
        for game_data in games["current"]:
            if not game_data.get("start_time") or not game_data.get("end_time"):
                continue
                
            # 检查游戏是否已存在
            existing_game = repo.get_game_by_name(game_data["name"])
            if not existing_game:
                game_create = FreeGameCreate(**game_data)
                new_game = repo.create_game(game_create)
                stored_games.append(new_game)
                logger.info(f"新增本周免费游戏: {new_game.name}")
            else:
                # TODO: 更新逻辑
                pass
        
        # 处理下周预告游戏
        for game_data in games["upcoming"]:
            if not game_data.get("start_time") or not game_data.get("end_time"):
                continue
                
            existing_game = repo.get_game_by_name(game_data["name"])
            if not existing_game:
                game_create = FreeGameCreate(**game_data)
                new_game = repo.create_game(game_create)
                stored_games.append(new_game)
                logger.info(f"新增下周预告游戏: {new_game.name}")
            else:
                pass
                
    except Exception as e:
        logger.error(f"存储游戏数据失败: {e}")
    finally:
        db.close()
    
    return games

if __name__ == "__main__":
    games = fetch_and_store_games()
    # Serialize datetime objects for printing
    def default(o):
        if isinstance(o, (datetime)):
            return o.isoformat()
    print(json.dumps(games, default=default, ensure_ascii=False, indent=2))
