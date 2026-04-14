#!/bin/bash
# 清理并重新部署

echo "=== 清理并重新部署 ==="

# 1. 停止并删除所有相关容器
echo "1. 清理容器..."
sudo docker stop $(sudo docker ps -a | grep -E 'game_claim|build' | awk '{print $1}') 2>/dev/null || true
sudo docker rm $(sudo docker ps -a | grep -E 'game_claim|build' | awk '{print $1}') 2>/dev/null || true

# 2. 删除未标记的镜像
echo "2. 清理镜像..."
sudo docker rmi $(sudo docker images -f "dangling=true" -q) 2>/dev/null || true

# 3. 清理构建缓存
echo "3. 清理缓存..."
sudo docker system prune -f

# 4. 解压代码
echo "4. 解压代码..."
cd /opt/docker/python/game_claim_helper
sudo tar xzf /tmp/game_claim_helper.tar.gz --overwrite

# 5. 构建镜像
echo "5. 构建镜像..."
sudo docker build -t game_claim_helper:latest . 2>&1

# 6. 启动容器
echo "6. 启动容器..."
sudo docker run -d --name game_claim_helper \
  --network host \
  --env-file /opt/docker/python/game_claim_helper/.env \
  -v /var/log/game_claim_helper:/app/logs \
  --restart unless-stopped \
  game_claim_helper:latest

# 7. 检查状态
echo "7. 检查状态..."
sleep 5
sudo docker ps | grep game_claim_helper
sudo docker logs --tail 20 game_claim_helper

echo "=== 完成 ==="
