#!/usr/bin/env python3
"""
修复页面访问问题
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
    print("=== 修复页面访问问题 ===")
    
    client = create_ssh_client()
    
    try:
        # 检查 Nginx 配置
        print("\n1. 检查 Nginx 配置...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cat /etc/nginx/nginx.conf 2>/dev/null | head -50", "Nginx主配置")
        
        # 检查 sites-enabled
        print("\n2. 检查 sites 配置...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S ls -la /etc/nginx/sites-enabled/ 2>/dev/null", "sites配置")
        
        # 检查是否有反向代理配置
        print("\n3. 检查反向代理配置...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S grep -r '8000\|proxy_pass' /etc/nginx/ 2>/dev/null | head -20", "反向代理")
        
        # 外部访问测试
        print("\n4. 外部访问测试...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -o /dev/null -w '%{{http_code}}' http://yxbot.online/games/view 2>&1", "外部访问")
        
        # 检查防火墙
        print("\n5. 检查防火墙...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S ufw status 2>/dev/null || echo 'ufw not enabled'", "防火墙")
        
    except Exception as e:
        print(f"\n修复失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
