#!/usr/bin/env python3
"""
验证游戏数据
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
        
        print("=== 验证游戏数据 ===\n")
        
        # 1. 刷新游戏数据
        print("1. 刷新游戏数据:")
        output = run_command(client, "curl -s -X POST http://localhost:8000/games/refresh")
        print(output)
        
        # 2. 检查 Redis 数据
        print("\n2. 检查 Redis 中的游戏数据:")
        output = run_command(client, "redis-cli -a redis1024@q GET 'game_claim:games:current' 2>/dev/null | python3 -m json.tool | head -50")
        print(output if output else "  无数据")
        
        # 3. 测试 API 获取当前游戏
        print("\n3. 测试 API 获取当前游戏:")
        output = run_command(client, "curl -s http://localhost:8000/games/current | python3 -m json.tool | head -30")
        print(output if output else "  无响应")
        
        # 4. 检查容器日志
        print("\n4. 容器日志:")
        output = run_command(client, "sudo docker logs --tail 20 game_claim_helper 2>&1")
        print(output)
        
    except Exception as e:
        print(f"验证失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
