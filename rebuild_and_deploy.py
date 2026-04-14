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
    client.connect(HOST, username=USER, password=PASSWORD, timeout=60)
    return client

def run_command(client, cmd, timeout=300):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    output = stdout.read().decode('utf-8', errors='ignore')
    return output

def main():
    client = None
    try:
        client = create_ssh_client()
        
        print("=== 重新构建并部署 ===\n")
        
        # 1. 上传代码包
        print("1. 上传代码包...")
        sftp = client.open_sftp()
        sftp.put('/tmp/game_claim_helper.tar.gz', '/tmp/game_claim_helper.tar.gz')
        sftp.close()
        print("上传完成!")
        
        # 2. 停止并删除旧容器
        print("\n2. 停止并删除旧容器...")
        run_command(client, "sudo docker stop game_claim_helper 2>/dev/null || true", 60)
        run_command(client, "sudo docker rm game_claim_helper 2>/dev/null || true", 60)
        print("旧容器已删除")
        
        # 3. 删除旧镜像
        print("\n3. 删除旧镜像...")
        run_command(client, "sudo docker rmi game_claim_helper:latest 2>/dev/null || true", 60)
        print("旧镜像已删除")
        
        # 4. 解压代码
        print("\n4. 解压代码...")
        run_command(client, f"cd {REMOTE_PATH} && sudo tar xzf /tmp/game_claim_helper.tar.gz --overwrite", 60)
        print("解压完成!")
        
        # 5. 构建新镜像
        print("\n5. 构建新镜像（这可能需要10-15分钟）...")
        output = run_command(client, f"cd {REMOTE_PATH} && sudo docker build -t game_claim_helper:latest .", 900)
        print(output[-2000:] if len(output) > 2000 else output)
        
        # 6. 启动新容器
        print("\n6. 启动新容器...")
        output = run_command(client, f"sudo docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper:latest", 60)
        print(output)
        
        # 7. 等待并检查状态
        print("\n7. 等待容器启动...")
        time.sleep(10)
        
        print("\n8. 检查容器状态...")
        output = run_command(client, "sudo docker ps | grep game_claim_helper", 30)
        print(output)
        
        # 8. 查看日志
        print("\n9. 查看最新日志...")
        output = run_command(client, "sudo docker logs --tail 30 game_claim_helper 2>&1", 30)
        print(output)
        
        print("\n=== 部署完成 ===")
        print("访问地址: https://yxbot.online/wechat/callback")
        
    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
