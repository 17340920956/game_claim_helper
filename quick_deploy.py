#!/usr/bin/env python3
"""
快速部署 - 只更新代码并重启容器
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

def run_command(client, cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    output = stdout.read().decode('utf-8', errors='ignore')
    return output

def main():
    client = None
    try:
        client = create_ssh_client()
        
        print("=== 快速部署 ===\n")
        
        # 1. 上传代码包
        print("1. 上传代码包...")
        sftp = client.open_sftp()
        sftp.put('/tmp/game_claim_helper.tar.gz', '/tmp/game_claim_helper.tar.gz')
        sftp.close()
        print("上传完成!")
        
        # 2. 解压代码
        print("\n2. 解压代码...")
        run_command(client, f"cd {REMOTE_PATH} && sudo tar xzf /tmp/game_claim_helper.tar.gz --overwrite", 60)
        print("解压完成!")
        
        # 3. 重启容器
        print("\n3. 重启容器...")
        run_command(client, "sudo docker restart game_claim_helper", 60)
        print("容器已重启!")
        
        # 4. 等待并检查状态
        print("\n4. 等待容器启动...")
        time.sleep(5)
        
        print("\n5. 检查容器状态...")
        output = run_command(client, "sudo docker ps | grep game_claim_helper", 30)
        print(output)
        
        # 5. 查看日志
        print("\n6. 查看最新日志...")
        output = run_command(client, "sudo docker logs --tail 20 game_claim_helper 2>&1", 30)
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
