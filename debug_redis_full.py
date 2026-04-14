#!/usr/bin/env python3
"""
完整调试 Redis 连接
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
        
        print("=== 完整调试 Redis 连接 ===\n")
        
        # 创建完整的测试脚本
        test_script = '''
import sys
sys.path.insert(0, '/app')
import os

# 打印环境变量
print("=== 环境变量 ===")
print("REDIS_URL:", os.environ.get('REDIS_URL', 'NOT SET'))
print("REDIS_PASSWORD:", os.environ.get('REDIS_PASSWORD', 'NOT SET'))

# 导入并测试配置
print("\\n=== 配置解析 ===")
from app.core.config import get_settings
settings = get_settings()
print("Settings REDIS_URL:", settings.REDIS_URL)
print("Settings REDIS_PASSWORD:", repr(settings.REDIS_PASSWORD))
print("Settings REDIS_HOST:", settings.REDIS_HOST)
print("Settings REDIS_PORT:", settings.REDIS_PORT)
print("Settings REDIS_DB:", settings.REDIS_DB)

# 测试 Redis 连接
print("\\n=== Redis 连接测试 ===")
import redis
try:
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True,
        socket_connect_timeout=5
    )
    print("Ping:", r.ping())
    r.set('test_key', 'test_value', ex=60)
    print("Set test_key: OK")
    print("Get test_key:", r.get('test_key'))
    r.delete('test_key')
    print("Delete test_key: OK")
except Exception as e:
    print("Redis Error:", e)
'''
        
        # 写入并执行
        run_command(client, f"cat > /tmp/test_full.py << 'EOF'{test_script}EOF")
        run_command(client, "sudo docker cp /tmp/test_full.py game_claim_helper:/tmp/test_full.py")
        output = run_command(client, "sudo docker exec game_claim_helper python3 /tmp/test_full.py")
        print(output)
        
    except Exception as e:
        print(f"调试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
