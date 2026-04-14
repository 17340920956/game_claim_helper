#!/usr/bin/env python3
"""
检查服务器状态
"""
import paramiko

HOST = "101.42.17.176"
USER = "ubuntu"
PASSWORD = "Yang1024@q"

def create_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=60)
    return client

def run_command(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    output = stdout.read().decode('utf-8', errors='ignore')
    return output

def main():
    client = None
    try:
        client = create_ssh_client()
        
        print("=== 检查服务器状态 ===\n")
        
        # 1. 检查容器状态
        print("1. 容器状态:")
        output = run_command(client, "sudo docker ps -a | grep game_claim_helper")
        print(output if output else "  无容器运行")
        
        # 2. 检查容器日志
        print("\n2. 容器日志 (最后30行):")
        output = run_command(client, "sudo docker logs --tail 30 game_claim_helper 2>&1")
        print(output if output else "  无日志")
        
        # 3. 检查Nginx状态
        print("\n3. Nginx状态:")
        output = run_command(client, "sudo systemctl status nginx | head -10")
        print(output)
        
        # 4. 测试本地接口
        print("\n4. 测试本地接口:")
        output = run_command(client, "curl -s http://localhost:8000/health")
        print(output if output else "  无响应")
        
    except Exception as e:
        print(f"检查失败: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
