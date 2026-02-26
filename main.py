from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from contextlib import asynccontextmanager

from database import get_db
from models import User, PushLog, ContactType, PushStatus, ConfirmationStatus
from schemas import (
    UserCreate, UserResponse, 
    GameInfo, PushLogResponse,
    ConfirmationRequest, PushRequest
)
from redis_client import redis_client
from push_service import push_service
from scraper import fetch_and_store_games
from scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield


app = FastAPI(
    title="Epic免费游戏推送系统",
    description="自动爬取Epic免费游戏并推送到微信/QQ",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/games/current", response_model=List[GameInfo])
def get_current_games():
    games = redis_client.get_current_week_games()
    return games


@app.get("/games/next", response_model=List[GameInfo])
def get_next_games():
    games = redis_client.get_next_week_games()
    return games


@app.post("/games/refresh")
def refresh_games():
    games = fetch_and_store_games()
    return {
        "message": "游戏数据已刷新",
        "current_count": len(games["current"]),
        "upcoming_count": len(games["upcoming"])
    }


@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        User.contact_type == user.contact_type,
        User.contact_id == user.contact_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该联系方式已绑定"
        )
    
    db_user = User(
        epic_account=user.epic_account,
        contact_type=user.contact_type,
        contact_id=user.contact_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    db.delete(user)
    db.commit()
    return {"message": "用户已删除"}


@app.post("/push")
def push_message(request: PushRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    games = redis_client.get_current_week_games()
    game = next((g for g in games if g.get("slug") == request.game_slug), None)
    
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    
    if redis_client.is_user_notified(request.game_slug, request.user_id):
        return {"message": "用户已收到通知", "already_notified": True}
    
    result = push_service.push_game_notification(
        contact_type=user.contact_type.value,
        contact_id=user.contact_id,
        game=game,
        is_next_week=False
    )
    
    push_status = PushStatus.success if result["success"] else PushStatus.failed
    
    message = f"游戏: {game.get('title')}"
    
    push_log = PushLog(
        user_id=user.id,
        game_slug=request.game_slug,
        game_title=game.get("title", ""),
        contact_type=user.contact_type,
        contact_id=user.contact_id,
        status=push_status,
        message=message,
        error_msg=result.get("error"),
        is_next_week=False
    )
    db.add(push_log)
    db.commit()
    
    if result["success"]:
        redis_client.add_notified_user(request.game_slug, request.user_id)
        redis_client.update_user_status(
            request.game_slug, 
            request.user_id, 
            "pending"
        )
    
    return {
        "success": result["success"],
        "error": result.get("error"),
        "log_id": push_log.id
    }


@app.post("/push/all")
def push_to_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    games = redis_client.get_current_week_games()
    
    if not games:
        return {"message": "没有本周免费游戏", "pushed_count": 0}
    
    results = []
    
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
            
            results.append({
                "user_id": user.id,
                "game": game.get("title"),
                "success": result["success"]
            })
    
    db.commit()
    
    success_count = sum(1 for r in results if r["success"])
    return {
        "message": f"推送完成",
        "total": len(results),
        "success_count": success_count,
        "failed_count": len(results) - success_count
    }


@app.post("/push/next-week")
def push_next_week_to_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    games = redis_client.get_next_week_games()
    
    if not games:
        return {"message": "没有下周预告游戏", "pushed_count": 0}
    
    results = []
    
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
            
            results.append({
                "user_id": user.id,
                "game": game.get("title"),
                "success": result["success"]
            })
    
    db.commit()
    
    success_count = sum(1 for r in results if r["success"])
    return {
        "message": "下周预告推送完成",
        "total": len(results),
        "success_count": success_count,
        "failed_count": len(results) - success_count
    }


@app.post("/confirmation")
def confirm_message(request: ConfirmationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    action = request.action.lower()
    if action not in ["confirmed", "claimed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action必须是confirmed或claimed"
        )
    
    push_log = db.query(PushLog).filter(
        PushLog.user_id == request.user_id,
        PushLog.game_slug == request.game_slug,
        PushLog.confirmation_status == ConfirmationStatus.pending
    ).first()
    
    if not push_log:
        return {"message": "没有待确认的记录", "already_processed": True}
    
    push_log.confirmation_status = ConfirmationStatus(action)
    push_log.confirmation_time = datetime.now()
    db.commit()
    
    redis_client.update_user_status(
        request.game_slug,
        request.user_id,
        action,
        is_next_week=push_log.is_next_week
    )
    
    return {
        "message": "确认成功",
        "status": action,
        "game_title": push_log.game_title
    }


@app.get("/logs", response_model=List[PushLogResponse])
def list_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(PushLog).order_by(PushLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs


@app.get("/logs/user/{user_id}", response_model=List[PushLogResponse])
def get_user_logs(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(PushLog).filter(PushLog.user_id == user_id).order_by(PushLog.created_at.desc()).all()
    return logs


@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
