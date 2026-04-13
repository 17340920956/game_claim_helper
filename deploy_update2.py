#!/usr/bin/env python3
"""
部署更新 - 调整图片大小
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
    print("=== 部署更新 - 调整图片大小 ===")
    
    client = create_ssh_client()
    
    try:
        # 上传到 /tmp
        print("\n1. 上传文件到 /tmp...")
        sftp = paramiko.SFTPClient.from_transport(client.get_transport())
        sftp.put("/Users/chen/codeRepository/game_claim_helper/app/templates/games.html", 
                 "/tmp/games.html")
        print("上传完成!")
        
        # 复制到目标目录
        print("\n2. 复制到项目目录...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cp /tmp/games.html {REMOTE_PATH}/app/templates/games.html", "复制文件")
        
        # 重启容器
        print("\n3. 重启容器...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker restart game_claim_helper", "重启容器")
        
        # 等待启动
        print("\n4. 等待容器启动...")
        time.sleep(5)
        
        # 检查状态
        print("\n5. 检查容器状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps | grep game_claim_helper", "检查状态")
        
        # 测试访问
        print("\n6. 测试页面访问...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -o /dev/null -w '%{{http_code}}' http://localhost/games/view", "测试访问")
        
        print("\n=== 部署完成 ===")
        print("图片高度已调整为: 电脑端 240px, 移动端 200px")
        
    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
