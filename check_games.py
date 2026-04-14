#!/usr/bin/env python3
"""
检查 Redis 中的游戏数据
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
        
        print("=== 检查游戏数据 ===\n")
        
        # 1. 检查 Redis 中的游戏数据
        print("1. 本周免费游戏:")
        output = run_command(client, "redis-cli -a redis1024@q GET 'game_claim:games:current' | python3 -m json.tool 2>/dev/null || echo '无数据'")
        print(output[:2000] if len(output) > 2000 else output)
        
        print("\n2. 下周预告游戏:")
        output = run_command(client, "redis-cli -a redis1024@q GET 'game_claim:games:upcoming' | python3 -m json.tool 2>/dev/null || echo '无数据'")
        print(output[:2000] if len(output) > 2000 else output)
        
        # 3. 检查所有 Redis key
        print("\n3. 所有 Redis keys:")
        output = run_command(client, "redis-cli -a redis1024@q KEYS '*'")
        print(output if output else "  无")
        
        # 4. 手动触发刷新
        print("\n4. 手动触发游戏数据刷新:")
        output = run_command(client, "curl -s -X POST http://localhost:8000/games/refresh")
        print(output)
        
        # 5. 再次检查
        print("\n5. 刷新后的本周游戏:")
        output = run_command(client, "redis-cli -a redis1024@q GET 'game_claim:games:current' | python3 -m json.tool 2>/dev/null | head -50 || echo '无数据'")
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
