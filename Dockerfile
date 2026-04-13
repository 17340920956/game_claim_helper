# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装必要工具 + Playwright/Chromium 依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    # Playwright & Chromium 系统依赖
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 fonts-noto-cjk \
    # 额外依赖（Playwright 需要）
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 设置pip超时和重试
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRY_COUNT=5

# 复制依赖文件并安装依赖（使用国内镜像源）
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 300 --retries 5 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt || \
    pip install --no-cache-dir --timeout 300 --retries 5 -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt || \
    pip install --no-cache-dir --timeout 300 --retries 5 -r requirements.txt

# 设置 Playwright 环境变量
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright

# 复制项目文件
COPY . .

# 创建浏览器安装脚本
RUN echo '#!/bin/bash\n\
set -e\n\
echo "=== 开始安装 Playwright 浏览器 ==="\n\
export PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright\n\
if [ -d "$PLAYWRIGHT_BROWSERS_PATH/chromium-"* ] && [ -f "$PLAYWRIGHT_BROWSERS_PATH/chromium-"*/chrome-linux/chrome ]; then\n\
    echo "浏览器已安装，跳过安装步骤"\n\
    ls -la $PLAYWRIGHT_BROWSERS_PATH/\n\
    exit 0\n\
fi\n\
echo "安装 Chromium 浏览器..."\n\
playwright install chromium\n\
echo "=== 浏览器安装完成 ==="\n\
ls -la $PLAYWRIGHT_BROWSERS_PATH/' > /tmp/install_browser.sh && chmod +x /tmp/install_browser.sh

# 暴露端口
EXPOSE 8000

# 使用启动脚本（先安装浏览器，再启动应用）
CMD ["bash", "-c", "bash /tmp/install_browser.sh && gunicorn -c gunicorn_conf.py app.main:app"]
