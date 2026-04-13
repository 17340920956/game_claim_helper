#!/usr/bin/env python3
"""
检查页面服务状态
"""
import paramiko
import sys

HOST = "101.42.17.176"
USER = "ubuntu"
PASSWORD = "Yang1024@q"

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
    print("=== 检查页面服务状态 ===")
    
    client = create_ssh_client()
    
    try:
        # 检查容器状态
        print("\n1. 检查容器状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps | grep game_claim_helper", "容器状态")
        
        # 检查日志
        print("\n2. 检查最近日志...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker logs --tail 30 game_claim_helper 2>&1", "查看日志")
        
        # 本地测试
        print("\n3. 本地测试页面...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -o /dev/null -w '%{{http_code}}' http://localhost:8000/games/view", "HTTP状态码")
        
        # 检查模板文件
        print("\n4. 检查模板文件...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S ls -la /opt/docker/python/game_claim_helper/app/templates/", "模板文件")
        
    except Exception as e:
        print(f"\n检查失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
