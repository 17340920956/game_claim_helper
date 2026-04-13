#!/bin/bash
# 服务器端部署脚本

set -e

echo "=== 在服务器上执行部署 ==="

REMOTE_PATH="/opt/docker/python/game_claim_helper"

cd $REMOTE_PATH

# 1. 解压代码
echo "1. 解压代码..."
tar xzf /tmp/game_claim_helper.tar.gz --overwrite 2>/dev/null || true

# 2. 停止旧容器
echo "2. 停止旧容器..."
docker stop game_claim_helper 2>/dev/null || true
docker rm game_claim_helper 2>/dev/null || true

# 3. 构建新镜像
echo "3. 构建新镜像..."
docker build -t game_claim_helper:latest .

# 4. 启动新容器
echo "4. 启动新容器..."
docker run -d \
    --name game_claim_helper \
    --network host \
    --env-file $REMOTE_PATH/.env \
    -v /var/log/game_claim_helper:/app/logs \
    -v /tmp:/tmp \
    --restart unless-stopped \
    game_claim_helper:latest

# 5. 检查状态
echo "5. 检查容器状态..."
docker ps -a | grep game_claim_helper

# 6. 清理
echo "6. 清理无用镜像..."
docker image prune -f 2>/dev/null || true

echo ""
echo "=== 部署完成 ==="
echo "查看日志: docker logs -f game_claim_helper"
