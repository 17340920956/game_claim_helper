#!/usr/bin/env python3
"""
部署修复 - 事件循环和链接问题
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
    print("=== 部署修复 ===")
    
    client = create_ssh_client()
    
    try:
        # 上传修改后的文件
        print("\n1. 上传 claim_service.py...")
        sftp = paramiko.SFTPClient.from_transport(client.get_transport())
        sftp.put("/Users/chen/codeRepository/game_claim_helper/app/services/game/claim_service.py", 
                 "/tmp/claim_service.py")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cp /tmp/claim_service.py {REMOTE_PATH}/app/services/game/claim_service.py", "复制文件")
        
        print("\n2. 上传 requirements.txt...")
        sftp.put("/Users/chen/codeRepository/game_claim_helper/requirements.txt", 
                 "/tmp/requirements.txt")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cp /tmp/requirements.txt {REMOTE_PATH}/requirements.txt", "复制文件")
        
        # 停止并删除旧容器
        print("\n3. 停止旧容器...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker stop game_claim_helper 2>/dev/null || true", "停止容器")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker rm game_claim_helper 2>/dev/null || true", "删除容器")
        
        # 删除旧镜像
        print("\n4. 删除旧镜像...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker rmi game_claim_helper-app:latest 2>/dev/null || true", "删除镜像")
        
        # 重新构建镜像
        print("\n5. 重新构建镜像（约需5-10分钟）...")
        build_cmd = f"cd {REMOTE_PATH} && docker build --no-cache -t game_claim_helper-app:latest ."
        stdin, stdout, stderr = client.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{build_cmd}'", get_pty=True, timeout=600)
        stdin.write(PASSWORD + '\n')
        stdin.flush()
        
        # 实时读取输出
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                line = stdout.channel.recv(1024).decode()
                if PASSWORD not in line:
                    print(line, end='')
        
        remaining = stdout.read().decode()
        if remaining and PASSWORD not in remaining:
            print(remaining)
        
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            print(f"构建失败，退出码: {exit_code}")
            return
        
        print("\n镜像构建成功!")
        
        # 启动容器
        print("\n6. 启动容器...")
        run_command(
            client,
            f"echo '{PASSWORD}' | sudo -S docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs -v /tmp:/tmp --restart unless-stopped game_claim_helper-app:latest",
            "启动容器",
            timeout=30
        )
        
        # 等待启动
        print("\n7. 等待容器启动...")
        time.sleep(5)
        
        # 检查状态
        print("\n8. 检查容器状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps | grep game_claim_helper", "检查状态")
        
        # 测试访问
        print("\n9. 测试页面访问...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -o /dev/null -w '%{{http_code}}' http://localhost/games/view", "测试访问")
        
        print("\n=== 部署完成 ===")
        print("修复内容：")
        print("1. 添加 nest_asyncio 解决事件循环冲突")
        print("2. 修复 WECHAT_OFFICIAL_URL 环境变量")
        
    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
