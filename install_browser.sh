#!/bin/bash
# 在容器内安装 Playwright 浏览器

set -e

echo "=== 开始安装 Playwright 浏览器 ==="

export PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# 检查浏览器是否已安装
if [ -d "$PLAYWRIGHT_BROWSERS_PATH/chromium-"* ] && [ -f "$PLAYWRIGHT_BROWSERS_PATH/chromium-"*/chrome-linux/chrome ]; then
    echo "浏览器已安装，跳过安装步骤"
    ls -la $PLAYWRIGHT_BROWSERS_PATH/
    exit 0
fi

echo "安装 Chromium 浏览器..."
playwright install chromium

echo "=== 浏览器安装完成 ==="
ls -la $PLAYWRIGHT_BROWSERS_PATH/
