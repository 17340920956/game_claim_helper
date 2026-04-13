#!/usr/bin/env python3
"""
快速部署 - 使用已有镜像
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
    print("=== 快速部署 game_claim_helper ===")
    
    client = create_ssh_client()
    
    try:
        # 1. 停止并删除旧容器
        print("\n1. 清理旧容器...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker stop game_claim_helper 2>/dev/null || true", "停止容器")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker rm game_claim_helper 2>/dev/null || true", "删除容器")
        
        # 2. 查看可用镜像
        print("\n2. 查看可用镜像...")
        output, _ = run_command(client, f"echo '{PASSWORD}' | sudo -S docker images", "查看镜像")
        
        # 3. 使用已有的 app 镜像启动
        print("\n3. 启动容器 (使用已有镜像)...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper-app:latest",
            "启动容器",
            timeout=30
        )
        
        # 4. 等待并检查状态
        print("\n4. 等待容器启动...")
        time.sleep(5)
        
        print("\n5. 检查容器状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps | grep game_claim_helper", "查看运行状态")
        
        print("\n6. 查看日志...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker logs --tail 50 game_claim_helper 2>&1", "查看日志")
        
        print("\n=== 部署完成 ===")
        
    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
