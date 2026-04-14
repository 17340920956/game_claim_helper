#!/usr/bin/env python3
"""
测试配置解析
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
        
        print("=== 测试配置解析 ===\n")
        
        # 创建测试脚本
        test_script = '''
import sys
sys.path.insert(0, '/app')

# 先打印环境变量
import os
print("Environment REDIS_URL:", os.environ.get('REDIS_URL', 'NOT SET'))
print("Environment REDIS_PASSWORD:", os.environ.get('REDIS_PASSWORD', 'NOT SET'))

# 然后导入配置
from app.core.config import get_settings
settings = get_settings()
print("Settings REDIS_URL:", settings.REDIS_URL)
print("Settings REDIS_PASSWORD:", settings.REDIS_PASSWORD[:10] + '...' if settings.REDIS_PASSWORD else 'EMPTY')
print("Settings REDIS_HOST:", settings.REDIS_HOST)
'''
        
        # 写入文件并执行
        run_command(client, f"cat > /tmp/test_cfg.py << 'EOF'{test_script}EOF")
        run_command(client, "sudo docker cp /tmp/test_cfg.py game_claim_helper:/tmp/test_cfg.py")
        output = run_command(client, "sudo docker exec game_claim_helper python3 /tmp/test_cfg.py")
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
