# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装必要工具
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 设置pip超时和重试
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRY_COUNT=5

# 复制依赖文件并安装依赖（使用国内镜像源）
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 300 --retries 5 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt || \
    pip install --no-cache-dir --timeout 300 --retries 5 -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt || \
    pip install --no-cache-dir --timeout 300 --retries 5 -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 使用 Gunicorn 启动应用
CMD ["gunicorn", "-c", "gunicorn_conf.py", "app.main:app"]
