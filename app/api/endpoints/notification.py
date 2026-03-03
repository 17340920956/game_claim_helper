from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.base import PushRequest, PushLogResponse, PushLogCreate
from app.repositories.user.user_repository import UserRepository
from app.repositories.game.game_repository import GameRepository
from app.repositories.notification.push_log_repository import PushLogRepository
from app.services.notification.notification_service import push_service
from app.core.security import verify_admin_access

router = APIRouter(tags=["Notifications"])

@router.post("/push")
def push_message(request: PushRequest, db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    user = user_repo.get_user(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    game_repo = GameRepository(db)
    game = game_repo.get_game(request.game_id)
    
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    
    log_repo = PushLogRepository(db)
    if log_repo.has_user_been_notified(request.user_id, request.game_id):
        return {"message": "用户已收到通知", "already_notified": True}
    
    # Determine if it is next week's game based on start time?
    # Or just push. The service handles formatting.
    # The request doesn't specify if it is next week.
    # We can check game.start_time vs now, but simpler to just push.
    
    result = push_service.push_game_notification(
        user=user,
        game=game,
        is_next_week=False # Assuming manual push is for current/active games
    )
    
    log_data = PushLogCreate(
        user_id=user.id,
        game_id=game.id,
        status=result["success"],
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
    user_repo = UserRepository(db)
    users = user_repo.get_all_users()
    
    game_repo = GameRepository(db)
    games = game_repo.get_active_games()
    
    if not games:
        return {"message": "没有本周免费游戏", "pushed_count": 0}
    
    results = []
    log_repo = PushLogRepository(db)
    
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
            
            results.append({
                "user_id": user.id,
                "game": game.name,
                "success": result["success"]
            })
    
    success_count = sum(1 for r in results if r["success"])
    return {
        "message": f"推送完成",
        "total": len(results),
        "success_count": success_count,
        "failed_count": len(results) - success_count
    }

@router.post("/push/next-week")
def push_next_week_to_all_users(db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    users = user_repo.get_all_users()
    
    game_repo = GameRepository(db)
    games = game_repo.get_upcoming_games()
    
    if not games:
        return {"message": "没有下周预告游戏", "pushed_count": 0}
    
    results = []
    log_repo = PushLogRepository(db)
    
    for user in users:
        # Check if we already notified about these upcoming games?
        # Usually we notify once.
        # But upcoming games might change or we might notify multiple times?
        # Let's assume we check if notified.
        
        games_to_push = []
        for game in games:
            if not log_repo.has_user_been_notified(user.id, game.id):
                games_to_push.append(game)
        
        if not games_to_push:
            continue

        # Batch push for upcoming games is usually better
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
            
            results.append({
                "user_id": user.id,
                "game": game.name,
                "success": result["success"]
            })
    
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
