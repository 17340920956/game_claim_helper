from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.db.redis import redis_client
from app.schemas.base import PushLogResponse, PushLogCreate
from app.repositories.user.user_repository import UserRepository
from app.repositories.notification.push_log_repository import PushLogRepository
from app.services.notification.notification_service import push_service
from app.core.security import verify_admin_access

router = APIRouter(tags=["Notifications"])


@router.post("/push/manual")
def push_message_manual(
    user_id: int,
    game_name: str,
    db: Session = Depends(get_db)
):
    """手动推送游戏通知给指定用户"""
    user_repo = UserRepository(db)
    user = user_repo.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 从 Redis 获取当前游戏列表
    games = redis_client.get_current_week_games()
    game_data = None
    for game in games:
        if game.get('name') == game_name:
            game_data = game
            break
    
    if not game_data:
        raise HTTPException(status_code=404, detail="游戏不存在")

    log_repo = PushLogRepository(db)
    game_slug = game_data.get('note') or game_data.get('name', 'unknown')
    if log_repo.has_user_been_notified(int(user.id), str(game_slug), is_next_week=False):
        return {"message": "用户已收到通知", "already_notified": True}

    result = push_service.push_game_notification(
        user=user, game=game_data, is_next_week=False
    )

    log_data = PushLogCreate(
        user_id=int(user.id),
        game_name=game_data.get('name', '未知'),
        game_slug=str(game_slug),
        status=result["success"],
        is_next_week=False,
        note=result.get("error")
    )
    push_log = log_repo.create_log(log_data)

    return {
        "success": result["success"],
        "error": result.get("error"),
        "log_id": push_log.id
    }


@router.post("/push/all")
def push_to_all_users(db: Session = Depends(get_db)):
    """推送本周游戏通知给所有用户"""
    user_repo = UserRepository(db)
    users = user_repo.get_all_users()

    # 从 Redis 获取当前游戏列表
    games = redis_client.get_current_week_games()
    if not games:
        return {"message": "没有本周免费游戏", "pushed_count": 0}

    results = []
    log_repo = PushLogRepository(db)

    for user in users:
        for game in games:
            game_slug = game.get('note') or game.get('name', 'unknown')
            if log_repo.has_user_been_notified(int(user.id), str(game_slug), is_next_week=False):
                continue

            result = push_service.push_game_notification(
                user=user, game=game, is_next_week=False
            )

            log_data = PushLogCreate(
                user_id=int(user.id),
                game_name=game.get('name', '未知'),
                game_slug=str(game_slug),
                status=result["success"],
                is_next_week=False,
                note=result.get("error")
            )
            log_repo.create_log(log_data)
            results.append({"user_id": int(user.id), "game": game.get('name'), "success": result["success"]})

    success_count = sum(1 for r in results if r["success"])
    return {
        "message": "推送完成",
        "total": len(results),
        "success_count": success_count,
        "failed_count": len(results) - success_count
    }


@router.post("/push/next-week")
def push_next_week_to_all_users(db: Session = Depends(get_db)):
    """推送下周预告通知给所有用户"""
    user_repo = UserRepository(db)
    users = user_repo.get_all_users()

    # 从 Redis 获取下周游戏列表
    games = redis_client.get_next_week_games()
    if not games:
        return {"message": "没有下周预告游戏", "pushed_count": 0}

    results = []
    log_repo = PushLogRepository(db)

    for user in users:
        games_to_push = []
        for game in games:
            game_slug = game.get('note') or game.get('name', 'unknown')
            if not log_repo.has_user_been_notified(int(user.id), str(game_slug), is_next_week=True):
                games_to_push.append(game)
        
        if not games_to_push:
            continue

        result = push_service.push_games_batch(
            user=user, games=games_to_push, is_next_week=True
        )

        for game in games_to_push:
            log_data = PushLogCreate(
                user_id=int(user.id),
                game_name=game.get('name', '未知'),
                game_slug=str(game.get('note') or game.get('name', 'unknown')),
                status=result["success"],
                is_next_week=True,
                note=result.get("error")
            )
            log_repo.create_log(log_data)
            results.append({"user_id": int(user.id), "game": game.get('name'), "success": result["success"]})

    success_count = sum(1 for r in results if r["success"])
    return {
        "message": "下周预告推送完成",
        "total": len(results),
        "success_count": success_count,
        "failed_count": len(results) - success_count
    }


@router.get("/logs", response_model=List[PushLogResponse], dependencies=[Depends(verify_admin_access)])
def list_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = PushLogRepository(db)
    return repo.list_logs(skip, limit)


@router.get("/logs/user/{user_id}", response_model=List[PushLogResponse], dependencies=[Depends(verify_admin_access)])
def get_user_logs(user_id: int, db: Session = Depends(get_db)):
    repo = PushLogRepository(db)
    return repo.get_user_logs(user_id)
