#!/usr/bin/env python3
"""
调试 Redis 配置
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
        
        print("=== 调试 Redis 配置 ===\n")
        
        # 检查容器内的环境变量
        print("1. 容器内的 REDIS_URL:")
        output = run_command(client, "sudo docker exec game_claim_helper env | grep REDIS")
        print(output)
        
        # 创建一个测试脚本来检查配置
        print("\n2. 测试配置解析:")
        test_script = '''
import os
print("REDIS_URL:", os.environ.get("REDIS_URL", "NOT SET"))
print("REDIS_PASSWORD:", os.environ.get("REDIS_PASSWORD", "NOT SET"))
'''
        # 写入临时文件
        run_command(client, f"echo '{test_script}' > /tmp/test_env.py")
        output = run_command(client, "sudo docker cp /tmp/test_env.py game_claim_helper:/tmp/test_env.py && sudo docker exec game_claim_helper python3 /tmp/test_env.py")
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
