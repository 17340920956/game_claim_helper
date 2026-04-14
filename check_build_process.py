#!/usr/bin/env python3
"""
检查构建进程状态
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
        
        print("=== 检查构建进程 ===\n")
        
        # 检查构建进程
        print("1. 构建进程:")
        output = run_command(client, "ps aux | grep -E 'docker|pip' | grep -v grep")
        print(output if output else "  无")
        
        # 检查最近日志
        print("\n2. 构建日志 (最后30行):")
        output = run_command(client, "sudo tail -30 /tmp/build.log 2>/dev/null || echo '无日志'")
        print(output)
        
        # 检查Docker状态
        print("\n3. Docker状态:")
        output = run_command(client, "sudo docker ps -a | head -5")
        print(output)
        
        # 检查镜像
        print("\n4. 镜像:")
        output = run_command(client, "sudo docker images | head -5")
        print(output)
        
    except Exception as e:
        print(f"检查失败: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
