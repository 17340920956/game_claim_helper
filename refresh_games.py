#!/usr/bin/env python3
"""
手动刷新游戏数据并检查
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
        
        print("=== 手动刷新游戏数据 ===\n")
        
        # 1. 先检查 Redis 密码配置
        print("1. 检查 Redis 密码是否正确解析:")
        test_code = """from app.core.config import get_settings; s = get_settings(); print(f'Password: {s.REDIS_PASSWORD[:5]}...' if s.REDIS_PASSWORD else 'Empty')"""
        output = run_command(client, f"cd /opt/docker/python/game_claim_helper && sudo docker exec game_claim_helper python3 -c '{test_code}'")
        print(output)
        
        # 2. 手动触发刷新
        print("\n2. 触发游戏数据刷新:")
        output = run_command(client, "curl -s -X POST http://localhost:8000/games/refresh")
        print(output)
        
        # 3. 检查新 key
        print("\n3. 检查新 key (game_claim:games:current):")
        output = run_command(client, "redis-cli -a redis1024@q GET 'game_claim:games:current' 2>/dev/null | head -200")
        print(output)
        
        # 4. 检查容器日志
        print("\n4. 容器日志:")
        output = run_command(client, "sudo docker logs --tail 30 game_claim_helper 2>&1")
        print(output)
        
    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
