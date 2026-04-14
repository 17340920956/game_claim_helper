#!/usr/bin/env python3
"""
部署脚本 - 简化版
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
        
        print("=== 开始部署 ===\n")
        
        # 1. 打包并上传代码
        print("1. 打包并上传代码...")
        import subprocess
        subprocess.run(["git", "archive", "-o", "/tmp/game_claim_helper.tar.gz", "HEAD"], check=True)
        
        sftp = client.open_sftp()
        sftp.put('/tmp/game_claim_helper.tar.gz', '/tmp/game_claim_helper.tar.gz')
        sftp.close()
        print("上传完成!")
        
        # 2. 停止旧容器
        print("\n2. 停止旧容器...")
        run_command(client, "sudo docker stop game_claim_helper 2>/dev/null || true")
        run_command(client, "sudo docker rm game_claim_helper 2>/dev/null || true")
        print("旧容器已停止")
        
        # 3. 解压代码
        print("\n3. 解压代码...")
        run_command(client, f"cd {REMOTE_PATH} && sudo tar xzf /tmp/game_claim_helper.tar.gz --overwrite")
        print("解压完成!")
        
        # 4. 构建镜像（后台运行）
        print("\n4. 构建镜像（后台运行，约5-10分钟）...")
        run_command(client, f"cd {REMOTE_PATH} && sudo docker build -t game_claim_helper:latest . > /tmp/build.log 2>&1")
        
        # 检查构建结果
        output = run_command(client, "tail -20 /tmp/build.log")
        if "Successfully tagged" in output or "successfully built" in output:
            print("镜像构建成功!")
        else:
            print("构建日志:")
            print(output)
            print("\n请检查构建日志: /tmp/build.log")
            return
        
        # 5. 启动新容器
        print("\n5. 启动新容器...")
        output = run_command(client, f"sudo docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs --restart unless-stopped game_claim_helper:latest")
        print(f"容器ID: {output[:20]}...")
        
        # 6. 等待启动
        print("\n6. 等待服务启动...")
        time.sleep(5)
        
        # 7. 检查状态
        print("\n7. 检查容器状态...")
        output = run_command(client, "sudo docker ps | grep game_claim_helper")
        if "game_claim_helper" in output:
            print("✓ 容器运行中")
        else:
            print("✗ 容器未运行")
            output = run_command(client, "sudo docker logs game_claim_helper 2>&1 | tail -30")
            print("错误日志:", output)
            return
        
        # 8. 查看日志
        print("\n8. 查看最新日志...")
        output = run_command(client, "sudo docker logs --tail 15 game_claim_helper 2>&1")
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
