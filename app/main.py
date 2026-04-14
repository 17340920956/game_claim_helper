from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from contextlib import asynccontextmanager
import os
import uvicorn

from app.core.scheduler import start_scheduler
from app.core.logger import logger
from app.api.endpoints.wechat import router as wechat_router
from app.api.endpoints.game import router as game_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    应用生命周期管理
    - 启动时：启动定时任务调度器
    - 关闭时：执行清理操作（目前为空）
    """
    start_scheduler()
    logger.info("Scheduler started.")
    yield


app = FastAPI(
    title="Epic免费游戏推送系统",
    description="自动爬取Epic免费游戏并推送到微信公众号",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yxbot.online", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# 注册路由模块
app.include_router(wechat_router)
app.include_router(game_router)


@app.get("/health")
def health_check():
    """
    健康检查接口
    """
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/MP_verify_{filename}.txt")
async def serve_wechat_verify_file(filename: str):
    """
    微信公众号域名归属权验证文件服务
    匹配根目录下以 MP_verify_ 开头的 .txt 文件
    """
    file_path = f"MP_verify_{filename}.txt"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        return PlainTextResponse(content)
    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
