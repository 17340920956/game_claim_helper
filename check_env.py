#!/usr/bin/env python3
"""
检查环境变量
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
        
        print("=== 检查环境变量 ===\n")
        
        # 检查 .env 文件
        print("1. Redis 配置:")
        output = run_command(client, "grep -E 'REDIS|DATABASE' /opt/docker/python/game_claim_helper/.env")
        print(output if output else "  未找到")
        
        # 测试 Redis 连接
        print("\n2. 测试 Redis 连接:")
        output = run_command(client, "redis-cli ping")
        print(f"  {output}")
        
        # 检查 Redis 认证
        print("\n3. 检查 Redis 是否需要密码:")
        output = run_command(client, "redis-cli INFO 2>&1 | head -5")
        print(f"  {output}")
        
    except Exception as e:
        print(f"检查失败: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
