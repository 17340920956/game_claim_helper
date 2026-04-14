#!/usr/bin/env python3
"""
检查 Docker 状态
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
        
        print("=== 检查 Docker 状态 ===\n")
        
        # 检查 Docker 服务
        print("1. Docker 服务状态:")
        output = run_command(client, "sudo systemctl status docker | head -10")
        print(output)
        
        # 检查正在运行的容器
        print("\n2. 运行中的容器:")
        output = run_command(client, "sudo docker ps")
        print(output if output else "  无")
        
        # 检查所有容器
        print("\n3. 所有容器:")
        output = run_command(client, "sudo docker ps -a")
        print(output if output else "  无")
        
        # 检查镜像
        print("\n4. Docker 镜像:")
        output = run_command(client, "sudo docker images")
        print(output if output else "  无")
        
        # 检查构建缓存
        print("\n5. 构建缓存:")
        output = run_command(client, "sudo docker system df")
        print(output)
        
        # 检查磁盘空间
        print("\n6. 磁盘空间:")
        output = run_command(client, "df -h /")
        print(output)
        
        # 检查内存
        print("\n7. 内存使用:")
        output = run_command(client, "free -h")
        print(output)
        
    except Exception as e:
        print(f"检查失败: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
