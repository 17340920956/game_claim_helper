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

# 复制依赖文件并安装依赖（使用国内镜像源）
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt || \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 及 Chromium（使用国内镜像源）
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple playwright || pip install --no-cache-dir playwright
RUN playwright install chromium --with-deps || playwright install chromium

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 使用 Gunicorn 启动应用
CMD ["gunicorn", "-c", "gunicorn_conf.py", "app.main:app"]