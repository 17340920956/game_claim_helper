# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装必要工具
# default-libmysqlclient-dev 需要 pkg-config 和 gcc
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 使用 Gunicorn 启动应用
CMD ["gunicorn", "-c", "gunicorn_conf.py", "app.main:app"]