#!/usr/bin/env python3
"""
测试 Redis 连接
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
        
        print("=== 测试 Redis 连接 ===\n")
        
        # 检查 .env 文件中的 REDIS_URL
        print("1. .env 文件中的 REDIS_URL:")
        output = run_command(client, "grep REDIS /opt/docker/python/game_claim_helper/.env")
        print(output)
        
        # 测试带密码的 Redis 连接
        print("\n2. 测试带密码连接:")
        output = run_command(client, "redis-cli -a redis1024@q ping 2>/dev/null")
        print(f"  结果: {output}")
        
        # 测试 Python 中的配置解析
        print("\n3. 测试 Python 配置解析:")
        test_code = """
import sys
sys.path.insert(0, '/opt/docker/python/game_claim_helper')
from app.core.config import get_settings
settings = get_settings()
print(f"REDIS_URL: {settings.REDIS_URL}")
print(f"REDIS_PASSWORD: {settings.REDIS_PASSWORD}")
print(f"REDIS_HOST: {settings.REDIS_HOST}")
"""
        output = run_command(client, f"cd /opt/docker/python/game_claim_helper && python3 -c '{test_code}'")
        print(output)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
