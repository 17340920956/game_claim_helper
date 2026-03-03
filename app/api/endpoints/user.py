from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.base import UserCreate, UserResponse
from app.core.security import verify_admin_access
from app.repositories.user.user_repository import UserRepository

router = APIRouter(tags=["Users"])

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    
    if user.wx_id:
        existing = repo.get_user_by_wx_id(user.wx_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该微信号已绑定"
            )
            
    if user.qq_id:
        existing = repo.get_user_by_qq_id(user.qq_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该QQ号已绑定"
            )
            
    return repo.create_user(user)

@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(verify_admin_access)])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    return repo.list_users(skip, limit)

@router.get("/users/{user_id}", response_model=UserResponse, dependencies=[Depends(verify_admin_access)])
def get_user(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.delete("/users/{user_id}", dependencies=[Depends(verify_admin_access)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    success = repo.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在或删除失败")
    return {"message": "用户已删除"}
