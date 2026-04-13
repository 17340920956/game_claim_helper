#!/usr/bin/env python3
"""
测试 HTTPS 访问
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
    print("=== 测试 HTTPS 访问 ===")
    
    client = create_ssh_client()
    
    try:
        # 测试 HTTP 访问 games/view
        print("\n1. 测试 HTTP 访问 /games/view...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -o /dev/null -w '%{{http_code}}' http://localhost/games/view", "HTTP本地")
        
        # 测试 HTTPS 访问
        print("\n2. 测试 HTTPS 访问 /games/view...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -k -o /dev/null -w '%{{http_code}}' https://localhost/games/view", "HTTPS本地")
        
        # 跟随重定向测试
        print("\n3. 跟随重定向测试...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -L -o /dev/null -w '%{{http_code}}' http://yxbot.online/games/view", "跟随重定向")
        
        # 检查 SSL 证书
        print("\n4. 检查 SSL 证书...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S ls -la /etc/nginx/ssl/", "SSL证书")
        
    except Exception as e:
        print(f"\n测试失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
