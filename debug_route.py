#!/usr/bin/env python3
"""
调试路由问题
"""
import paramiko
import sys

HOST = "101.42.17.176"
USER = "ubuntu"
PASSWORD = "Yang1024@q"
REMOTE_PATH = "/opt/docker/python/game_claim_helper"

def create_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    return client

def run_command(client, cmd, description="", timeout=60):
    if description:
        print(f"\n>>> {description}")
    print(f"执行: {cmd[:80]}...")
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    output = stdout.read().decode()
    error = stderr.read().decode()
    if output:
        lines = output.split('\n')
        filtered = [l for l in lines if PASSWORD not in l]
        if filtered:
            print('\n'.join(filtered[-50:]))
    if error and 'WARNING' not in error:
        print(f"错误: {error[:500]}", file=sys.stderr)
    return output, error

def main():
    print("=== 调试路由问题 ===")
    
    client = create_ssh_client()
    
    try:
        # 检查 main.py 内容
        print("\n1. 检查 main.py 中的路由...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cat {REMOTE_PATH}/app/main.py | grep -A 5 'games'", "检查main.py")
        
        # 检查 game.py 路由
        print("\n2. 检查 game.py 中的路由...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S grep -n 'games/view' {REMOTE_PATH}/app/api/endpoints/game.py", "检查game.py")
        
        # 检查模板文件是否存在
        print("\n3. 检查模板文件...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S ls -la {REMOTE_PATH}/app/templates/", "检查模板")
        
        # 检查所有路由
        print("\n4. 检查所有路由...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s http://localhost:8000/docs 2>&1 | head -20", "检查docs")
        
    except Exception as e:
        print(f"\n调试失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
