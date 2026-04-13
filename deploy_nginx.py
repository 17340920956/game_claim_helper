#!/usr/bin/env python3
"""
部署 Nginx 配置
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
    print("=== 部署 Nginx 配置 ===")
    
    client = create_ssh_client()
    
    try:
        # 上传配置文件
        print("\n1. 上传配置文件...")
        sftp = paramiko.SFTPClient.from_transport(client.get_transport())
        sftp.put("/Users/chen/codeRepository/game_claim_helper/nginx_game_claim_helper.conf", "/tmp/nginx_game_claim_helper.conf")
        print("上传完成!")
        
        # 复制到 Nginx 目录
        print("\n2. 复制到 Nginx 目录...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cp /tmp/nginx_game_claim_helper.conf /etc/nginx/sites-available/game_claim_helper", "复制配置")
        
        # 创建软链接
        print("\n3. 创建软链接...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S ln -sf /etc/nginx/sites-available/game_claim_helper /etc/nginx/sites-enabled/", "创建软链接")
        
        # 测试配置
        print("\n4. 测试配置...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S nginx -t", "测试配置")
        
        # 重载 Nginx
        print("\n5. 重载 Nginx...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S systemctl reload nginx", "重载Nginx")
        
        # 测试访问
        print("\n6. 测试 HTTP 访问...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -o /dev/null -w '%{{http_code}}' http://localhost/games/view", "HTTP测试")
        
        print("\n=== 部署完成 ===")
        
    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
