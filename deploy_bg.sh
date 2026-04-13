#!/bin/bash
# 后台部署脚本 - 在服务器上执行

REMOTE_PATH="/opt/docker/python/game_claim_helper"
LOG_FILE="/tmp/deploy_$(date +%Y%m%d_%H%M%S).log"

echo "=== 开始后台部署 ===" | tee -a $LOG_FILE
echo "日志文件: $LOG_FILE" | tee -a $LOG_FILE

cd $REMOTE_PATH

# 1. 解压代码
echo "1. 解压代码..." | tee -a $LOG_FILE
tar xzf /tmp/game_claim_helper.tar.gz --overwrite 2>/dev/null || true

# 2. 停止旧容器
echo "2. 停止旧容器..." | tee -a $LOG_FILE
docker stop game_claim_helper 2>/dev/null || true
docker rm game_claim_helper 2>/dev/null || true

# 3. 构建新镜像
echo "3. 构建新镜像..." | tee -a $LOG_FILE
docker build -t game_claim_helper:latest . 2>&1 | tee -a $LOG_FILE

# 4. 启动新容器
echo "4. 启动新容器..." | tee -a $LOG_FILE
docker run -d \
    --name game_claim_helper \
    --network host \
    --env-file $REMOTE_PATH/.env \
    -v /var/log/game_claim_helper:/app/logs \
    -v /tmp:/tmp \
    --restart unless-stopped \
    game_claim_helper:latest 2>&1 | tee -a $LOG_FILE

# 5. 检查状态
echo "5. 检查容器状态..." | tee -a $LOG_FILE
docker ps -a | grep game_claim_helper | tee -a $LOG_FILE

# 6. 清理
echo "6. 清理无用镜像..." | tee -a $LOG_FILE
docker image prune -f 2>/dev/null || true

echo "" | tee -a $LOG_FILE
echo "=== 部署完成 ===" | tee -a $LOG_FILE
echo "查看日志: docker logs -f game_claim_helper" | tee -a $LOG_FILE
