#!/bin/bash
# 在服务器上手动执行

cd /opt/docker/python/game_claim_helper

# 停止旧容器
sudo docker stop game_claim_helper 2>/dev/null || true
sudo docker rm game_claim_helper 2>/dev/null || true

# 解压代码
sudo tar xzf /tmp/game_claim_helper.tar.gz --overwrite

# 构建镜像
echo "开始构建镜像..."
sudo docker build -t game_claim_helper:latest .

# 启动容器
echo "启动容器..."
sudo docker run -d --name game_claim_helper \
  --network host \
  --env-file /opt/docker/python/game_claim_helper/.env \
  -v /var/log/game_claim_helper:/app/logs \
  --restart unless-stopped \
  game_claim_helper:latest

# 查看状态
echo "容器状态:"
sudo docker ps | grep game_claim_helper

# 查看日志
echo "容器日志:"
sleep 3
sudo docker logs --tail 20 game_claim_helper
