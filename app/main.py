from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from contextlib import asynccontextmanager
import os
import uvicorn

from app.core.scheduler import start_scheduler
from app.core.logger import logger
from app.db.session import engine, Base
from app.api.endpoints.wechat import router as wechat_router
from app.api.endpoints.user import router as user_router
from app.api.endpoints.game import router as game_router
from app.api.endpoints.notification import router as notification_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    - 启动时：初始化并启动定时任务调度器
    - 关闭时：执行清理操作（目前为空）
    """
    # 初始化数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized.")
    
    start_scheduler()
    yield

app = FastAPI(
    title="Epic免费游戏推送系统",
    description="自动爬取Epic免费游戏并推送到微信公众号/QQ",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由模块
app.include_router(wechat_router)
app.include_router(user_router)
app.include_router(game_router)
app.include_router(notification_router)

@app.get("/health")
def health_check():
    """
    健康检查接口
    """
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/{filename}")
async def serve_wechat_verify_file(filename: str):
    """
    通用微信公众号域名归属权验证文件服务
    自动匹配根目录下以 MP_verify_ 开头的 .txt 文件
    """
    from fastapi import HTTPException
    if filename.startswith("MP_verify_") and filename.endswith(".txt"):
        file_path = filename  # 假设文件在根目录
        if os.path.exists(file_path):
             with open(file_path, 'r') as f:
                 content = f.read()
             return PlainTextResponse(content)
    
    # 如果不匹配验证文件，抛出 404，由 FastAPI 继续处理或返回错误
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
