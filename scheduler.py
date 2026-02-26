from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from config import get_settings

settings = get_settings()

scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)


def scrape_current_week_games():
    from scraper import fetch_and_store_games
    from redis_client import redis_client
    
    print(f"[{datetime.now()}] 开始爬取本周免费游戏...")
    redis_client.clear_week_data(is_next_week=False)
    games = fetch_and_store_games()
    print(f"[{datetime.now()}] 本周游戏爬取完成: {len(games['current'])} 款")


def scrape_next_week_games():
    from scraper import fetch_and_store_games
    from redis_client import redis_client
    
    print(f"[{datetime.now()}] 开始爬取下周预告游戏...")
    redis_client.clear_week_data(is_next_week=True)
    games = fetch_and_store_games()
    print(f"[{datetime.now()}] 下周预告爬取完成: {len(games['upcoming'])} 款")


def push_current_week_notifications():
    from database import SessionLocal
    from models import User, PushLog, PushStatus
    from redis_client import redis_client
    from push_service import push_service
    
    print(f"[{datetime.now()}] 开始推送本周游戏通知...")
    
    db = SessionLocal()
    try:
        users = db.query(User).all()
        games = redis_client.get_current_week_games()
        
        if not games:
            print("没有本周免费游戏")
            return
        
        pushed_count = 0
        for user in users:
            for game in games:
                if redis_client.is_user_notified(game.get("slug"), user.id):
                    continue
                
                result = push_service.push_game_notification(
                    contact_type=user.contact_type.value,
                    contact_id=user.contact_id,
                    game=game,
                    is_next_week=False
                )
                
                push_status = PushStatus.success if result["success"] else PushStatus.failed
                
                push_log = PushLog(
                    user_id=user.id,
                    game_slug=game.get("slug", ""),
                    game_title=game.get("title", ""),
                    contact_type=user.contact_type,
                    contact_id=user.contact_id,
                    status=push_status,
                    message=f"游戏: {game.get('title')}",
                    error_msg=result.get("error"),
                    is_next_week=False
                )
                db.add(push_log)
                
                if result["success"]:
                    redis_client.add_notified_user(game.get("slug"), user.id)
                    redis_client.update_user_status(game.get("slug"), user.id, "pending")
                    pushed_count += 1
        
        db.commit()
        print(f"[{datetime.now()}] 本周游戏推送完成: {pushed_count} 条")
    except Exception as e:
        print(f"推送失败: {e}")
        db.rollback()
    finally:
        db.close()


def push_next_week_notifications():
    from database import SessionLocal
    from models import User, PushLog, PushStatus
    from redis_client import redis_client
    from push_service import push_service
    
    print(f"[{datetime.now()}] 开始推送下周预告通知...")
    
    db = SessionLocal()
    try:
        users = db.query(User).all()
        games = redis_client.get_next_week_games()
        
        if not games:
            print("没有下周预告游戏")
            return
        
        pushed_count = 0
        for user in users:
            for game in games:
                if redis_client.is_user_notified(game.get("slug"), user.id, is_next_week=True):
                    continue
                
                result = push_service.push_game_notification(
                    contact_type=user.contact_type.value,
                    contact_id=user.contact_id,
                    game=game,
                    is_next_week=True
                )
                
                push_status = PushStatus.success if result["success"] else PushStatus.failed
                
                push_log = PushLog(
                    user_id=user.id,
                    game_slug=game.get("slug", ""),
                    game_title=game.get("title", ""),
                    contact_type=user.contact_type,
                    contact_id=user.contact_id,
                    status=push_status,
                    message=f"下周预告: {game.get('title')}",
                    error_msg=result.get("error"),
                    is_next_week=True
                )
                db.add(push_log)
                
                if result["success"]:
                    redis_client.add_notified_user(game.get("slug"), user.id, is_next_week=True)
                    redis_client.update_user_status(game.get("slug"), user.id, "pending", is_next_week=True)
                    pushed_count += 1
        
        db.commit()
        print(f"[{datetime.now()}] 下周预告推送完成: {pushed_count} 条")
    except Exception as e:
        print(f"推送失败: {e}")
        db.rollback()
    finally:
        db.close()


def retry_failed_pushes():
    from database import SessionLocal
    from models import PushLog, PushStatus
    from push_service import push_service
    
    print(f"[{datetime.now()}] 开始重试失败的推送...")
    
    db = SessionLocal()
    try:
        failed_logs = db.query(PushLog).filter(
            PushLog.status == PushStatus.failed
        ).all()
        
        retry_count = 0
        for log in failed_logs:
            result = push_service.push_to_user(
                contact_type=log.contact_type.value,
                contact_id=log.contact_id,
                message=log.message
            )
            
            if result["success"]:
                log.status = PushStatus.success
                log.error_msg = None
                retry_count += 1
            else:
                log.error_msg = result.get("error")
        
        db.commit()
        print(f"[{datetime.now()}] 重试完成: {retry_count}/{len(failed_logs)} 成功")
    except Exception as e:
        print(f"重试失败: {e}")
        db.rollback()
    finally:
        db.close()


def setup_scheduler():
    scheduler.add_job(
        scrape_current_week_games,
        CronTrigger(day_of_week="tue", hour=0, minute=0),
        id="scrape_current_week",
        name="爬取本周免费游戏",
        replace_existing=True
    )
    
    scheduler.add_job(
        scrape_next_week_games,
        CronTrigger(day_of_week="fri", hour=0, minute=0),
        id="scrape_next_week",
        name="爬取下周预告游戏",
        replace_existing=True
    )
    
    scheduler.add_job(
        push_current_week_notifications,
        CronTrigger(day_of_week="wed", hour=10, minute=0),
        id="push_current_week",
        name="推送本周游戏通知",
        replace_existing=True
    )
    
    scheduler.add_job(
        push_next_week_notifications,
        CronTrigger(day_of_week="sat", hour=10, minute=0),
        id="push_next_week",
        name="推送下周预告通知",
        replace_existing=True
    )
    
    scheduler.add_job(
        retry_failed_pushes,
        CronTrigger(hour=12, minute=0),
        id="retry_failed",
        name="重试失败的推送",
        replace_existing=True
    )
    
    return scheduler


def start_scheduler():
    setup_scheduler()
    scheduler.start()
    print("定时任务调度器已启动")


if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("调度器已停止")
