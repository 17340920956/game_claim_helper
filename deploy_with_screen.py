#!/usr/bin/env python3
"""
使用screen在服务器后台执行部署
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
    print("=== 使用Screen部署 ===")
    
    client = None
    try:
        client = create_ssh_client()
        
        # 创建部署脚本
        deploy_script = f'''#!/bin/bash
set -e
cd {REMOTE_PATH}
echo "$(date): 开始部署..." > /tmp/deploy_screen.log

echo "$(date): 解压代码..." >> /tmp/deploy_screen.log
tar xzf /tmp/game_claim_helper.tar.gz --overwrite 2>/dev/null || true

echo "$(date): 停止旧容器..." >> /tmp/deploy_screen.log
docker stop game_claim_helper 2>/dev/null || true
docker rm game_claim_helper 2>/dev/null || true

echo "$(date): 构建镜像..." >> /tmp/deploy_screen.log
docker build -t game_claim_helper:latest . 2>&1 | tee -a /tmp/deploy_screen.log

echo "$(date): 启动容器..." >> /tmp/deploy_screen.log
docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper:latest 2>&1 | tee -a /tmp/deploy_screen.log

echo "$(date): 检查状态..." >> /tmp/deploy_screen.log
docker ps -a | grep game_claim_helper >> /tmp/deploy_screen.log

echo "$(date): 部署完成!" >> /tmp/deploy_screen.log
'''
        
        # 上传部署脚本
        print("1. 上传部署脚本...")
        sftp = client.open_sftp()
        with sftp.file('/tmp/deploy_in_screen.sh', 'w') as f:
            f.write(deploy_script)
        sftp.close()
        run_command(client, "chmod +x /tmp/deploy_in_screen.sh", 30)
        
        # 使用screen启动部署
        print("2. 在screen中启动部署...")
        run_command(client, "sudo screen -dmS deploy bash -c 'bash /tmp/deploy_in_screen.sh'", 30)
        
        print("3. 部署已在服务器后台启动...")
        print("等待构建完成（约5-10分钟）...")
        
        # 等待构建完成
        for i in range(60):  # 最多等待10分钟
            time.sleep(10)
            try:
                output = run_command(client, "sudo docker ps -a | grep game_claim_helper", 30)
                if "Up" in output:
                    print(f"\n✓ 容器已成功启动! (用时 {(i+1)*10}秒)")
                    break
                elif i % 6 == 0:  # 每分钟显示一次状态
                    print(f"  等待中... ({(i+1)*10}秒)")
            except:
                pass
        else:
            print("\n构建时间较长，请在服务器上检查状态")
        
        # 查看日志
        print("\n4. 查看部署日志...")
        output = run_command(client, "cat /tmp/deploy_screen.log 2>/dev/null | tail -100", 30)
        print(output)
        
        # 查看容器状态
        print("\n5. 容器状态...")
        output = run_command(client, "sudo docker ps -a | grep game_claim_helper", 30)
        print(output if output else "容器尚未启动")
        
        print("\n=== 部署状态 ===")
        print("访问地址: https://yxbot.online/wechat/callback")
        print("查看实时日志: ssh ubuntu@101.42.17.176 'sudo docker logs -f game_claim_helper'")
        print("查看部署日志: ssh ubuntu@101.42.17.176 'cat /tmp/deploy_screen.log'")
        
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
