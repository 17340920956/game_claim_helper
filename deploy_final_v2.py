#!/usr/bin/env python3
"""
最终版远程部署脚本 - 使用后台执行方式
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

def run_command(client, cmd, description="", timeout=60):
    """执行远程命令"""
    if description:
        print(f"\n>>> {description}")
    print(f"执行: {cmd[:60]}...")
    
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    # 过滤敏感信息
    lines = []
    for line in output.split('\n'):
        if PASSWORD not in line and line.strip():
            lines.append(line)
    
    if lines:
        print('\n'.join(lines[-50:]))
    
    if error and 'tar:' not in error:
        print(f"错误: {error[:500]}", file=sys.stderr)
    
    return lines, error

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

        # 2. 上传代码包和脚本
        print("\n2. 上传代码包...")
        scp = SCPClient(client.get_transport(), socket_timeout=120)
        scp.put("/tmp/game_claim_helper.tar.gz", "/tmp/game_claim_helper.tar.gz")
        scp.put("/Users/chen/codeRepository/game_claim_helper/deploy_bg.sh", "/tmp/deploy_bg.sh")
        print("上传完成!")
        scp.close()
        scp = None

        # 3. 在服务器上后台执行部署脚本
        print("\n3. 启动后台部署...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S nohup bash /tmp/deploy_bg.sh > /tmp/deploy_nohup.log 2>&1 &",
            "启动后台部署",
            timeout=30
        )

        print("\n部署已在服务器后台启动...")
        print("等待构建完成（约5-10分钟）...")
        
        # 等待构建完成
        time.sleep(10)
        
        # 检查部署状态
        for i in range(30):  # 最多等待5分钟
            time.sleep(10)
            try:
                output, _ = run_command(
                    client,
                    f"echo '{PASSWORD}' | sudo -S docker ps -a | grep game_claim_helper",
                    f"检查状态 ({i+1}/30)",
                    timeout=30
                )
                if output and "Up" in str(output):
                    print("\n✓ 容器已成功启动!")
                    break
            except:
                pass
        
        # 查看最终状态
        print("\n4. 查看容器状态...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker ps -a | grep game_claim_helper",
            "容器状态",
            timeout=30
        )

        print("\n5. 查看最新日志...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker logs --tail 30 game_claim_helper 2>&1",
            "查看日志",
            timeout=30
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
