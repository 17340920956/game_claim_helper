"""
Epic免费游戏推送系统 - FastAPI应用主入口

功能：
- 提供Epic免费游戏查询API
- 微信公众号消息处理
- 定时任务调度

技术栈：
- FastAPI: Web框架
- Redis: 数据缓存
- APScheduler: 定时任务
- WeChatPy: 微信开发
"""

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
    
    启动时：
    - 启动定时任务调度器（用于定期爬取游戏数据）
    
    关闭时：
    - 执行清理操作（目前为空）
    """
    start_scheduler()
    logger.info("Scheduler started.")
    yield


# FastAPI应用实例
app = FastAPI(
    title="Epic免费游戏推送系统",
    description="自动爬取Epic免费游戏并推送到微信公众号",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS中间件 - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yxbot.online", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# 注册路由模块
app.include_router(wechat_router)  # 微信公众号相关接口
app.include_router(game_router)    # 游戏查询相关接口


@app.get("/health")
def health_check():
    """
    健康检查接口
    
    用于：
    - 监控服务状态
    - 负载均衡健康检查
    
    返回：
    - status: healthy 表示服务正常
    - timestamp: 当前时间戳
    """
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/MP_verify_{filename}.txt")
async def serve_wechat_verify_file(filename: str):
    """
    微信公众号域名归属权验证文件服务
    
    微信要求将验证文件放在域名根目录下，用于证明域名所有权
    文件格式：MP_verify_xxxxxxxxxxxxxxxx.txt
    
    参数：
        filename: 验证文件名（不含.txt后缀）
    
    返回：
        验证文件内容（纯文本）
    
    异常：
        404: 文件不存在
    """
    file_path = f"MP_verify_{filename}.txt"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        return PlainTextResponse(content)
    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    # 开发环境直接运行
    # 生产环境使用Gunicorn启动
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
