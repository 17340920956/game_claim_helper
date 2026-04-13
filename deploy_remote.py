#!/usr/bin/env python3
"""
远程部署脚本 - 使用 paramiko 自动处理密码登录
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
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    return client

def run_command(client, cmd, description="", timeout=300):
    """执行远程命令"""
    if description:
        print(f"\n>>> {description}")
    print(f"执行: {cmd[:80]}...")
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    # 如果需要 sudo，输入密码
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    output = stdout.read().decode()
    error = stderr.read().decode()
    if output:
        # 过滤掉密码回显和tar警告
        lines = output.split('\n')
        filtered = []
        for line in lines:
            if PASSWORD in line:
                continue
            if 'tar: Ignoring unknown extended header' in line:
                continue
            if 'tar: Error exit delayed from previous errors' in line:
                continue
            filtered.append(line)
        if filtered:
            print('\n'.join(filtered[-50:]))  # 只显示最后50行
    if error and 'tar:' not in error:
        print(f"错误: {error[:500]}", file=sys.stderr)
    return output, error

def main():
    print("=== 开始远程部署 ===")
    print(f"目标服务器: {HOST}")
    print(f"部署路径: {REMOTE_PATH}")

    client = None
    scp = None
    
    try:
        # 1. 连接服务器
        print("\n1. 连接服务器...")
        client = create_ssh_client()
        print("连接成功!")

        # 2. 上传代码包
        print("\n2. 上传代码包...")
        scp = SCPClient(client.get_transport())
        scp.put("/tmp/game_claim_helper.tar.gz", "/tmp/game_claim_helper.tar.gz")
        print("上传完成!")

        # 3. 解压并部署 - 使用 sudo
        print("\n3. 解压代码...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S bash -c 'cd {REMOTE_PATH} && tar xzf /tmp/game_claim_helper.tar.gz --overwrite 2>/dev/null || true'", "解压代码")

        # 4. 停止旧容器
        print("\n4. 停止旧容器...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker stop game_claim_helper 2>/dev/null || true", "停止容器")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker rm game_claim_helper 2>/dev/null || true", "删除容器")

        # 5. 构建新镜像
        print("\n5. 构建新镜像 (这可能需要几分钟)...")
        output, error = run_command(
            client, 
            f"echo '{PASSWORD}' | sudo -S bash -c 'cd {REMOTE_PATH} && docker build -t game_claim_helper:latest .'",
            "构建镜像",
            timeout=600
        )

        # 6. 启动新容器
        print("\n6. 启动新容器...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper:latest",
            "启动容器"
        )

        # 7. 检查状态
        print("\n7. 检查容器状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps -a | grep game_claim_helper", "查看容器")

        # 8. 清理旧镜像
        print("\n8. 清理无用镜像...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker image prune -f 2>/dev/null || true", "清理镜像")

        # 9. 查看日志
        print("\n9. 查看最新日志...")
        time.sleep(3)  # 等待容器启动
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker logs --tail 30 game_claim_helper 2>&1", "查看日志")

        print("\n=== 部署完成 ===")
        print("查看实时日志: sudo docker logs -f game_claim_helper")

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
