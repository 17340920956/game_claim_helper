#!/usr/bin/env python3
"""
修复 HTTPS 访问问题
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
    print("=== 修复 HTTPS 访问问题 ===")
    
    client = create_ssh_client()
    
    try:
        # 检查 443 端口监听
        print("\n1. 检查 443 端口监听...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S netstat -tlnp | grep 443", "443端口")
        
        # 检查 Nginx 是否监听 443
        print("\n2. 检查 Nginx 监听状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S netstat -tlnp | grep nginx", "Nginx监听")
        
        # 重启 Nginx
        print("\n3. 重启 Nginx...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S systemctl restart nginx", "重启Nginx")
        
        # 检查 Nginx 状态
        print("\n4. 检查 Nginx 状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S systemctl status nginx | head -20", "Nginx状态")
        
        # 再次测试
        print("\n5. 再次测试 HTTPS...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -k -o /dev/null -w '%{{http_code}}' https://localhost/games/view", "HTTPS测试")
        
    except Exception as e:
        print(f"\n修复失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
