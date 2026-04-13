#!/usr/bin/env python3
"""
重新构建镜像并部署
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

def run_command(client, cmd, description="", timeout=120):
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
            print('\n'.join(filtered[-50:]))
    if error and 'WARNING' not in error:
        print(f"错误: {error[:500]}", file=sys.stderr)
    return output, error

def main():
    print("=== 重新构建镜像并部署 ===")
    
    client = create_ssh_client()
    
    try:
        # 1. 停止并删除旧容器
        print("\n1. 停止并删除旧容器...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker stop game_claim_helper 2>/dev/null || true", "停止容器")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker rm game_claim_helper 2>/dev/null || true", "删除容器")
        
        # 2. 删除旧镜像
        print("\n2. 删除旧镜像...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker rmi game_claim_helper-app:latest 2>/dev/null || true", "删除镜像")
        
        # 3. 重新构建镜像（不使用缓存）
        print("\n3. 重新构建镜像（约需5-10分钟）...")
        build_cmd = f"cd {REMOTE_PATH} && docker build --no-cache -t game_claim_helper-app:latest ."
        stdin, stdout, stderr = client.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{build_cmd}'", get_pty=True, timeout=600)
        stdin.write(PASSWORD + '\n')
        stdin.flush()
        
        # 实时读取输出
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                line = stdout.channel.recv(1024).decode()
                if PASSWORD not in line:
                    print(line, end='')
        
        remaining = stdout.read().decode()
        if remaining and PASSWORD not in remaining:
            print(remaining)
        
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            print(f"构建失败，退出码: {exit_code}")
            return
        
        print("\n镜像构建成功!")
        
        # 4. 启动容器
        print("\n4. 启动容器...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper-app:latest",
            "启动容器",
            timeout=30
        )
        
        # 5. 等待并测试
        print("\n5. 等待容器启动...")
        time.sleep(5)
        
        print("\n6. 测试网页访问...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s http://localhost:8000/games/view 2>&1 | head -30", "测试网页")
        
        print("\n=== 部署完成 ===")
        
    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
