#!/usr/bin/env python3
"""
检查刷新后的游戏数据
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
        
        print("=== 检查刷新后的游戏数据 ===\n")
        
        # 检查所有 keys
        print("1. 所有 Redis keys:")
        output = run_command(client, "redis-cli -a redis1024@q KEYS '*' 2>/dev/null | grep -v Warning")
        print(output if output else "  无")
        
        # 检查新 key 的数据
        print("\n2. 新 key (game_claim:games:current):")
        output = run_command(client, "redis-cli -a redis1024@q GET 'game_claim:games:current' 2>/dev/null | grep -v Warning")
        print(output[:1000] if len(output) > 1000 else output)
        
        # 检查旧 key 的数据
        print("\n3. 旧 key (free_games:current_week):")
        output = run_command(client, "redis-cli -a redis1024@q GET 'free_games:current_week' 2>/dev/null | grep -v Warning")
        print(output[:1000] if len(output) > 1000 else output)
        
        # 检查容器日志
        print("\n4. 容器日志 (最后20行):")
        output = run_command(client, "sudo docker logs --tail 20 game_claim_helper 2>&1")
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
