#!/bin/bash
# 在服务器上执行的部署脚本

set -e

echo "=== 开始部署 ==="

# 1. 停止旧容器
echo "1. 停止旧容器..."
sudo docker stop game_claim_helper 2>/dev/null || true
sudo docker rm game_claim_helper 2>/dev/null || true

# 2. 解压代码
echo "2. 解压代码..."
cd /opt/docker/python/game_claim_helper
sudo tar xzf /tmp/game_claim_helper.tar.gz --overwrite

# 3. 构建镜像
echo "3. 构建镜像..."
sudo docker build -t game_claim_helper:latest . 2>&1 | tee /tmp/build.log

# 4. 启动容器
echo "4. 启动容器..."
sudo docker run -d --name game_claim_helper \
  --network host \
  --env-file /opt/docker/python/game_claim_helper/.env \
  -v /var/log/game_claim_helper:/app/logs \
  --restart unless-stopped \
  game_claim_helper:latest

# 5. 等待启动
echo "5. 等待服务启动..."
sleep 5

# 6. 检查状态
echo "6. 检查容器状态..."
sudo docker ps | grep game_claim_helper

# 7. 查看日志
echo "7. 查看最新日志..."
sudo docker logs --tail 20 game_claim_helper 2>&1

echo "=== 部署完成 ==="
