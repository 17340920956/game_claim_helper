#!/usr/bin/env python3
"""
直接部署脚本 - 在服务器上直接执行所有命令
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
    transport = client.get_transport()
    if transport:
        transport.set_keepalive(30)
    return client

def run_command(client, cmd, description="", timeout=1200):
    if description:
        print(f"\n>>> {description}")
    print(f"执行: {cmd[:70]}...")
    
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    
    # 实时输出
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            data = stdout.channel.recv(4096).decode('utf-8', errors='ignore')
            lines = data.split('\n')
            for line in lines:
                if PASSWORD not in line and line.strip():
                    print(line)
        time.sleep(0.5)
    
    # 获取退出状态
    exit_code = stdout.channel.recv_exit_status()
    return exit_code

def main():
    print("=== 开始直接部署 ===")
    print(f"目标服务器: {HOST}")
    
    client = None
    
    try:
        # 连接服务器
        print("\n1. 连接服务器...")
        client = create_ssh_client()
        print("连接成功!")

        # 执行部署步骤
        commands = [
            (f"cd {REMOTE_PATH} && sudo tar xzf /tmp/game_claim_helper.tar.gz --overwrite", "解压代码", 60),
            ("sudo docker stop game_claim_helper 2>/dev/null || true", "停止旧容器", 30),
            ("sudo docker rm game_claim_helper 2>/dev/null || true", "删除旧容器", 30),
            (f"cd {REMOTE_PATH} && sudo docker build -t game_claim_helper:latest .", "构建镜像", 900),
            (f"sudo docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper:latest", "启动容器", 60),
            ("sudo docker ps -a | grep game_claim_helper", "检查容器状态", 30),
            ("sudo docker image prune -f 2>/dev/null || true", "清理镜像", 30),
        ]
        
        for i, (cmd, desc, timeout) in enumerate(commands, 2):
            print(f"\n{i}. {desc}...")
            exit_code = run_command(client, cmd, desc, timeout)
            if exit_code != 0 and "2>/dev/null" not in cmd:
                print(f"警告: 命令退出码 {exit_code}")
            time.sleep(2)

        # 查看日志
        print("\n查看容器日志...")
        time.sleep(5)
        run_command(client, "sudo docker logs --tail 50 game_claim_helper 2>&1", "查看日志", 30)

        print("\n=== 部署完成 ===")
        print("访问地址: https://yxbot.online/wechat/callback")

    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
