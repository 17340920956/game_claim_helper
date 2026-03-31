#!/bin/bash
# 确保脚本抛出遇到的错误
set -e

# 获取当前目录的父目录作为构建上下文
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting Docker build from $PROJECT_ROOT..."

# 切换到项目根目录执行构建
cd "$PROJECT_ROOT"

# 构建镜像
docker build -t game_claim_helper:latest .

echo "Docker build completed successfully."
echo "You can run the container using:"
echo "docker run -p 8000:8000 --env-file .env game_claim_helper:latest"
