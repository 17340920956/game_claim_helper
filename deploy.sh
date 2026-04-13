#!/bin/bash
# 部署脚本 - 在服务器上执行

set -e

echo "=== 开始部署 game_claim_helper ==="

# 1. 进入项目目录
cd /opt/docker/python/game_claim_helper

# 2. 拉取最新代码（如果有git）
if [ -d .git ]; then
    git pull origin main 2>/dev/null || echo "Git pull skipped"
fi

# 3. 停止并删除旧容器
echo "停止旧容器..."
docker stop game_claim_helper 2>/dev/null || true
docker rm game_claim_helper 2>/dev/null || true

# 4. 构建新镜像
echo "构建新镜像..."
docker build -t game_claim_helper:latest .

# 5. 启动新容器
echo "启动新容器..."
docker run -d \
    --name game_claim_helper \
    --network host \
    --env-file .env \
    -v /var/log/game_claim_helper:/app/logs \
    -v /tmp:/tmp \
    --restart unless-stopped \
    game_claim_helper:latest

# 6. 等待启动
sleep 3

# 7. 检查状态
echo "检查容器状态..."
docker ps -a | grep game_claim_helper

echo ""
echo "=== 部署完成 ==="
echo "查看日志: docker logs -f game_claim_helper"
