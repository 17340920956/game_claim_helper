#!/bin/bash
# 在服务器上手动安装 Playwright 浏览器

set -e

echo "=== 开始安装 Playwright 浏览器 ==="

# 设置环境变量
export PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright

# 安装 playwright pip 包
echo "1. 安装 playwright Python 包..."
pip install --no-cache-dir playwright

# 安装 chromium
echo "2. 下载 Chromium 浏览器..."
playwright install chromium

echo "3. 检查安装结果..."
ls -la $PLAYWRIGHT_BROWSERS_PATH/

echo "=== 浏览器安装完成 ==="
