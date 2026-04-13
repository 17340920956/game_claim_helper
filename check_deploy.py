#!/usr/bin/env python3
"""
检查部署状态并完成剩余步骤
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
        filtered = []
        for line in lines:
            if PASSWORD in line:
                continue
            filtered.append(line)
        if filtered:
            print('\n'.join(filtered[-30:]))
    if error:
        print(f"错误: {error[:500]}", file=sys.stderr)
    return output, error

def main():
    print("=== 检查部署状态 ===")
    
    client = create_ssh_client()
    
    try:
        # 检查容器状态
        print("\n1. 检查容器状态...")
        output, _ = run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps -a | grep game_claim_helper", "查看容器")
        
        # 如果容器不存在，启动它
        if "game_claim_helper" not in output:
            print("\n2. 容器未运行，启动新容器...")
            run_command(
                client,
                f"echo '{PASSWORD}' | sudo -S docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper:latest",
                "启动容器",
                timeout=30
            )
            time.sleep(3)
        else:
            print("容器已存在")
        
        # 检查容器是否健康
        print("\n3. 检查容器健康状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps | grep game_claim_helper", "检查运行状态")
        
        # 查看日志
        print("\n4. 查看最新日志...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker logs --tail 50 game_claim_helper 2>&1", "查看日志")
        
        # 清理无用镜像
        print("\n5. 清理无用镜像...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker image prune -f 2>/dev/null || true", "清理镜像")
        
        # 列出所有镜像
        print("\n6. 查看 Docker 镜像...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker images", "查看镜像")
        
        print("\n=== 部署状态检查完成 ===")
        
    except Exception as e:
        print(f"检查失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
