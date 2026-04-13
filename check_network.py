#!/usr/bin/env python3
"""
检查网络访问问题
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
    print("=== 检查网络访问问题 ===")
    
    client = create_ssh_client()
    
    try:
        # 检查防火墙
        print("\n1. 检查防火墙状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S ufw status", "防火墙")
        
        # 检查端口监听
        print("\n2. 检查 80 端口监听...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S netstat -tlnp | grep ':80'", "80端口")
        
        # 检查 Nginx 访问日志
        print("\n3. 检查 Nginx 访问日志...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S tail -10 /var/log/nginx/access.log", "访问日志")
        
        # 检查错误日志
        print("\n4. 检查 Nginx 错误日志...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S tail -10 /var/log/nginx/error.log", "错误日志")
        
    except Exception as e:
        print(f"\n检查失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
