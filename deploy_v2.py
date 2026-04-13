#!/usr/bin/env python3
"""
远程部署脚本 v2 - 分步骤执行，避免超时
"""
import paramiko
import sys
import time

HOST = "101.42.17.176"
USER = "ubuntu"
PASSWORD = "Yang1024@q"
REMOTE_PATH = "/opt/docker/python/game_claim_helper"

def create_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    return client

def run_command(client, cmd, description="", timeout=60):
    if description:
        print(f"\n>>> {description}")
    print(f"执行: {cmd[:80]}...")
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    output = stdout.read().decode()
    error = stderr.read().decode()
    if output:
        lines = output.split('\n')
        filtered = [l for l in lines if PASSWORD not in l]
        if filtered:
            print('\n'.join(filtered[-40:]))
    if error and 'WARNING' not in error:
        print(f"错误: {error[:500]}", file=sys.stderr)
    return output, error

def main():
    print("=== 重新部署 game_claim_helper ===")
    
    client = create_ssh_client()
    
    try:
        # 1. 停止并删除旧容器
        print("\n1. 清理旧容器...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker stop game_claim_helper 2>/dev/null || true", "停止容器")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker rm game_claim_helper 2>/dev/null || true", "删除容器")
        
        # 2. 使用已有的 Python 基础镜像，只安装依赖
        print("\n2. 创建简化 Dockerfile...")
        dockerfile_content = '''FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc default-libmysqlclient-dev pkg-config \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 和浏览器
RUN pip install playwright && \
    playwright install chromium

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "-t", "120", "--access-logfile", "-", "--error-logfile", "-", "app.main:app"]
'''
        
        # 写入 Dockerfile
        run_command(client, f"echo '{PASSWORD}' | sudo -S bash -c 'cat > {REMOTE_PATH}/Dockerfile' << 'EOF'\n{dockerfile_content}\nEOF", "创建 Dockerfile")
        
        # 3. 构建镜像 - 使用更长的超时
        print("\n3. 构建 Docker 镜像 (约需 5-10 分钟)...")
        print("开始构建，请耐心等待...")
        
        # 分步构建，先安装依赖
        build_cmd = f"cd {REMOTE_PATH} && docker build --no-cache -t game_claim_helper:latest ."
        
        # 执行构建命令，超时 10 分钟
        stdin, stdout, stderr = client.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{build_cmd}'", get_pty=True, timeout=600)
        stdin.write(PASSWORD + '\n')
        stdin.flush()
        
        # 实时读取输出
        output_lines = []
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                line = stdout.channel.recv(1024).decode()
                if PASSWORD not in line:
                    output_lines.append(line)
                    print(line, end='')
        
        # 获取剩余输出
        remaining = stdout.read().decode()
        if remaining and PASSWORD not in remaining:
            print(remaining)
        
        error = stderr.read().decode()
        if error and 'WARNING' not in error:
            print(f"构建错误: {error[:1000]}")
        
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            print(f"构建失败，退出码: {exit_code}")
            return
        
        print("\n镜像构建成功!")
        
        # 4. 启动容器
        print("\n4. 启动容器...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper:latest",
            "启动容器",
            timeout=30
        )
        
        # 5. 等待并检查状态
        print("\n5. 等待容器启动...")
        time.sleep(5)
        
        print("\n6. 检查容器状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps | grep game_claim_helper", "查看运行状态")
        
        print("\n7. 查看日志...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker logs --tail 30 game_claim_helper 2>&1", "查看日志")
        
        print("\n=== 部署完成 ===")
        
    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
