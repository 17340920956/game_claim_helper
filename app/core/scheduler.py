from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from app.core.config import get_settings
from app.services.game.scraper_service import fetch_and_store_games
from app.services.notification.notification_service import push_service
from app.models.base import User, PushLog, FreeGame
from app.db.session import SessionLocal
from app.repositories.game.game_repository import GameRepository
from app.repositories.user.user_repository import UserRepository
from app.repositories.notification.push_log_repository import PushLogRepository
from app.schemas.base import PushLogCreate
from app.core.logger import logger

settings = get_settings()

scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)


def scrape_current_week_games():
    """
    定时任务：爬取本周免费游戏
    """
    logger.info("开始爬取本周免费游戏...")
    games = fetch_and_store_games()
    logger.info(f"本周游戏爬取完成: {len(games['current'])} 款")


def scrape_next_week_games():
    """
    定时任务：爬取下周预告游戏
    """
    logger.info("开始爬取下周预告游戏...")
    games = fetch_and_store_games()
    logger.info(f"下周预告爬取完成: {len(games['upcoming'])} 款")


def push_current_week_notifications():
    """
    定时任务：推送本周游戏通知
    """
    logger.info("开始推送本周游戏通知...")
    
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        game_repo = GameRepository(db)
        log_repo = PushLogRepository(db)
        
        users = user_repo.get_all_users()
        games = game_repo.get_active_games()
        
        if not games:
            logger.warning("没有本周免费游戏")
            return
        
        pushed_count = 0
        for user in users:
            for game in games:
                if log_repo.has_user_been_notified(user.id, game.id):
                    continue
                
                result = push_service.push_game_notification(
                    user=user,
                    game=game,
                    is_next_week=False
                )
                
                log_data = PushLogCreate(
                    user_id=user.id,
                    game_id=game.id,
                    status=result["success"],
                    note=result.get("error")
                )
                log_repo.create_log(log_data)
                
                if result["success"]:
                    pushed_count += 1
        
        logger.info(f"本周游戏推送完成: {pushed_count} 条")
    except Exception as e:
        logger.exception(f"推送失败: {e}")
    finally:
        db.close()


def push_next_week_notifications():
    """
    定时任务：推送下周预告通知
    """
    logger.info("开始推送下周预告通知...")
    
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        game_repo = GameRepository(db)
        log_repo = PushLogRepository(db)
        
        users = user_repo.get_all_users()
        games = game_repo.get_upcoming_games()
        
        if not games:
            logger.warning("没有下周预告游戏")
            return
        
        pushed_count = 0
        for user in users:
            games_to_push = []
            for game in games:
                if not log_repo.has_user_been_notified(user.id, game.id):
                    games_to_push.append(game)
            
            if not games_to_push:
                continue

            result = push_service.push_games_batch(
                user=user,
                games=games_to_push,
                is_next_week=True
            )
            
            for game in games_to_push:
                log_data = PushLogCreate(
                    user_id=user.id,
                    game_id=game.id,
                    status=result["success"],
                    note=result.get("error")
                )
                log_repo.create_log(log_data)
                
                if result["success"]:
                    pushed_count += 1
        
        logger.info(f"下周预告推送完成: {pushed_count} 条")
    except Exception as e:
        logger.exception(f"推送失败: {e}")
    finally:
        db.close()


def retry_failed_pushes():
    """
    定时任务：重试失败的推送
    """
    logger.info("开始重试失败的推送...")
    
    db = SessionLocal()
    try:
        # Get logs where status is False (failed)
        # We might need a limit or retry count, but for now just retry all failed
        failed_logs = db.query(PushLog).filter(
            PushLog.status == False
        ).all()
        
        retry_count = 0
        for log in failed_logs:
            # Re-push using push_service.push_to_user
            # We need the message content. But PushLog no longer stores the message content.
            # We must reconstruct it from log.game.
            
            if not log.user or not log.game:
                continue
                
            # Determine if it was next week or current based on game start time?
            # Or just assume current format.
            # Or we can check if game is active.
            
            # Since we don't store "is_next_week" or message content, we have to guess or reconstruct.
            # Simplest is to treat as single game notification.
            
            result = push_service.push_game_notification(
                user=log.user,
                game=log.game,
                is_next_week=False # Assumption
            )
            
            if result["success"]:
                log.status = True
                log.note = "Retry success"
                retry_count += 1
            else:
                log.note = result.get("error")
        
        db.commit()
        logger.info(f"重试完成: {retry_count}/{len(failed_logs)} 成功")
    except Exception as e:
        logger.exception(f"重试失败: {e}")
    finally:
        db.close()


def start_scheduler():
    """
    配置并启动 APScheduler 调度器
    """
    # 每周四晚上 23:05 爬取本周免费游戏 (Epic通常在周四23:00更新)
    scheduler.add_job(
        scrape_current_week_games,
        CronTrigger(day_of_week='thu', hour=23, minute=5),
        id='scrape_current_week'
    )
    
    # 每周四晚上 23:05 爬取下周预告游戏
    scheduler.add_job(
        scrape_next_week_games,
        CronTrigger(day_of_week='thu', hour=23, minute=5),
        id='scrape_next_week'
    )
    
    # 每周五早上 09:00 推送本周游戏通知
    scheduler.add_job(
        push_current_week_notifications,
        CronTrigger(day_of_week='fri', hour=9, minute=0),
        id='push_current_week'
    )
    
    # 每周五早上 09:30 推送下周预告通知
    scheduler.add_job(
        push_next_week_notifications,
        CronTrigger(day_of_week='fri', hour=9, minute=30),
        id='push_next_week'
    )
    
    # 每天重试失败的推送
    scheduler.add_job(
        retry_failed_pushes,
        CronTrigger(hour='10-22', minute=0),  # 每天10点到22点的整点重试
        id='retry_failed_pushes'
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
