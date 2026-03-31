#!/bin/bash

echo "=========================================="
echo "启动 Game Claim Helper 服务"
echo "=========================================="

cd /opt/docker/python/game_claim_helper

# 激活虚拟环境
source venv/bin/activate

# 启动服务
nohup python3 run.py > logs/app.log 2>&1 &

echo "服务已启动"
echo "日志文件: logs/app.log"

# 等待服务启动
sleep 3

# 检查服务状态
if curl -s http://localhost:8000/health; then
    echo "✓ 服务运行正常"
else
    echo "✗ 服务启动失败，请检查日志"
    exit 1
fi
