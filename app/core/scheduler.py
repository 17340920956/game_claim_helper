from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import get_settings
from app.services.game.scraper_service import fetch_and_store_games
from app.core.logger import logger

settings = get_settings()

scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)


def scrape_current_week_games():
    """定时任务：爬取本周免费游戏"""
    logger.info("开始爬取本周免费游戏...")
    games = fetch_and_store_games()
    logger.info(f"本周游戏爬取完成: {len(games['current'])} 款")


def scrape_next_week_games():
    """定时任务：爬取下周预告游戏"""
    logger.info("开始爬取下周预告游戏...")
    games = fetch_and_store_games()
    logger.info(f"下周预告爬取完成: {len(games['upcoming'])} 款")


def start_scheduler():
    """配置并启动 APScheduler 调度器"""
    # 每周四晚上 23:05 爬取本周免费游戏
    scheduler.add_job(
        scrape_current_week_games,
        CronTrigger(day_of_week='thu', hour=23, minute=5),
        id='scrape_current_week'
    )

    # 每周四晚上 23:10 爬取下周预告游戏
    scheduler.add_job(
        scrape_next_week_games,
        CronTrigger(day_of_week='thu', hour=23, minute=10),
        id='scrape_next_week'
    )

    scheduler.start()
    logger.info("调度器已启动")


if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("调度器已停止")
