#!/usr/bin/env python3
"""
修复部署 - 手动执行步骤
"""
import paramiko
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
        
        print("=== 修复部署 ===\n")
        
        # 1. 检查构建进程
        print("1. 检查是否有卡住的构建进程...")
        output = run_command(client, "ps aux | grep -E 'docker|apt' | grep -v grep")
        if output:
            print(f"发现进程:\n{output}")
            print("\n停止卡住的进程...")
            run_command(client, "sudo pkill -f 'docker build' || true")
            time.sleep(2)
        else:
            print("  无卡住的进程")
        
        # 2. 检查镜像
        print("\n2. 检查镜像...")
        output = run_command(client, "sudo docker images | grep game_claim_helper")
        if output:
            print(f"镜像已存在:\n{output}")
        else:
            print("  镜像不存在，需要重新构建")
            print("\n3. 重新构建镜像...")
            print("  这可能需要5-10分钟，请耐心等待...")
            output = run_command(client, f"cd {REMOTE_PATH} && sudo docker build -t game_claim_helper:latest .", timeout=600)
            print(output[-1000:] if len(output) > 1000 else output)
        
        # 4. 启动容器
        print("\n4. 启动容器...")
        run_command(client, "sudo docker stop game_claim_helper 2>/dev/null || true")
        run_command(client, "sudo docker rm game_claim_helper 2>/dev/null || true")
        output = run_command(client, f"sudo docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs --restart unless-stopped game_claim_helper:latest")
        print(f"容器ID: {output[:30]}...")
        
        # 5. 等待并检查
        print("\n5. 等待服务启动...")
        time.sleep(5)
        
        print("\n6. 检查容器状态...")
        output = run_command(client, "sudo docker ps | grep game_claim_helper")
        if "game_claim_helper" in output:
            print("✓ 容器运行中")
            print(output)
        else:
            print("✗ 容器未运行")
            print("\n查看错误日志:")
            output = run_command(client, "sudo docker logs game_claim_helper 2>&1 | tail -30")
            print(output)
            return
        
        # 7. 测试接口
        print("\n7. 测试健康接口...")
        time.sleep(3)
        output = run_command(client, "curl -s http://localhost:8000/health")
        if output:
            print(f"响应: {output}")
        else:
            print("  无响应")
        
        print("\n=== 修复完成 ===")
        
    except Exception as e:
        print(f"\n修复失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
