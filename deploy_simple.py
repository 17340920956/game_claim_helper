#!/usr/bin/env python3
"""
简化版远程部署脚本 - 上传后在服务器端执行
"""
import paramiko
import os
import sys
import time
from scp import SCPClient

# 服务器配置
HOST = "101.42.17.176"
USER = "ubuntu"
PASSWORD = "Yang1024@q"
REMOTE_PATH = "/opt/docker/python/game_claim_helper"

def create_ssh_client():
    """创建 SSH 客户端"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=60)
    transport = client.get_transport()
    if transport:
        transport.set_keepalive(30)
    return client

def run_command(client, cmd, description="", timeout=1200):
    """执行远程命令"""
    if description:
        print(f"\n>>> {description}")
    print(f"执行: {cmd[:60]}...")
    
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    
    # 实时读取输出
    output_lines = []
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            data = stdout.channel.recv(1024).decode('utf-8', errors='ignore')
            lines = data.split('\n')
            for line in lines:
                if PASSWORD not in line and line.strip():
                    output_lines.append(line)
                    if len(output_lines) > 200:
                        output_lines.pop(0)
    
    # 读取剩余输出
    remaining = stdout.read().decode('utf-8', errors='ignore')
    if remaining:
        for line in remaining.split('\n'):
            if PASSWORD not in line and line.strip():
                output_lines.append(line)
    
    error = stderr.read().decode('utf-8', errors='ignore')
    
    # 显示最后100行
    if output_lines:
        print('\n'.join(output_lines[-100:]))
    
    if error and 'tar:' not in error and 'WARNING' not in error:
        print(f"错误: {error[:500]}", file=sys.stderr)
    
    return output_lines, error

def main():
    print("=== 开始远程部署 ===")
    print(f"目标服务器: {HOST}")
    
    client = None
    scp = None
    
    try:
        # 1. 连接服务器
        print("\n1. 连接服务器...")
        client = create_ssh_client()
        print("连接成功!")

        # 2. 上传代码包
        print("\n2. 上传代码包...")
        scp = SCPClient(client.get_transport(), socket_timeout=120)
        scp.put("/tmp/game_claim_helper.tar.gz", "/tmp/game_claim_helper.tar.gz")
        scp.put("/Users/chen/codeRepository/game_claim_helper/deploy_steps.sh", "/tmp/deploy_steps.sh")
        print("上传完成!")
        scp.close()
        scp = None

        # 3. 在服务器上执行部署脚本
        print("\n3. 执行部署脚本...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S bash /tmp/deploy_steps.sh",
            "执行部署",
            timeout=1200
        )

        # 4. 等待并检查状态
        print("\n4. 等待容器启动...")
        time.sleep(5)
        
        print("\n5. 检查容器状态...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker ps -a | grep game_claim_helper",
            "查看容器"
        )

        # 5. 查看日志
        print("\n6. 查看最新日志...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker logs --tail 50 game_claim_helper 2>&1",
            "查看日志"
        )

        print("\n=== 部署完成 ===")
        print("访问地址: https://yxbot.online/wechat/callback")
        print("查看实时日志: ssh ubuntu@101.42.17.176 'sudo docker logs -f game_claim_helper'")

    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if scp:
            try:
                scp.close()
            except:
                pass
        if client:
            try:
                client.close()
            except:
                pass

if __name__ == "__main__":
    main()
