#!/bin/bash
# 确保脚本抛出遇到的错误
set -e

echo "Starting Docker build..."

# 构建镜像
docker build -t game_claim_helper:latest .

echo "Docker build completed successfully."
echo "You can run the container using:"
echo "docker run -p 8000:8000 game_claim_helper:latest"
