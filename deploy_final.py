#!/usr/bin/env python3
"""
最终部署 - 修复路由问题
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
    print("=== 最终部署 - 修复路由 ===")
    
    client = create_ssh_client()
    
    try:
        # 1. 上传代码包
        print("\n1. 上传代码包...")
        scp = paramiko.SFTPClient.from_transport(client.get_transport())
        scp.put("/tmp/game_claim_helper_v3.tar.gz", "/tmp/game_claim_helper_v3.tar.gz")
        print("上传完成!")
        
        # 2. 停止容器
        print("\n2. 停止旧容器...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker stop game_claim_helper 2>/dev/null || true", "停止容器")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker rm game_claim_helper 2>/dev/null || true", "删除容器")
        
        # 3. 解压代码
        print("\n3. 解压代码...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S bash -c 'cd {REMOTE_PATH} && tar xzf /tmp/game_claim_helper_v3.tar.gz --overwrite 2>/dev/null || true'", "解压代码")
        
        # 4. 启动容器
        print("\n4. 启动容器...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper-app:latest",
            "启动容器",
            timeout=30
        )
        
        # 5. 等待并检查状态
        print("\n5. 等待容器启动...")
        time.sleep(5)
        
        print("\n6. 检查容器状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps | grep game_claim_helper", "查看运行状态")
        
        print("\n7. 测试网页访问...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s http://localhost:8000/games/view 2>&1 | head -30", "测试网页")
        
        print("\n=== 部署完成 ===")
        print("游戏展示网页地址: http://yxbot.online/games/view")
        
    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
