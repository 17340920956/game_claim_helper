#!/usr/bin/env python3
"""
更新 Nginx 配置
"""
import paramiko
import sys

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
        
        print("=== 更新 Nginx 配置 ===\n")
        
        # 上传配置文件
        print("1. 上传 Nginx 配置...")
        sftp = client.open_sftp()
        sftp.put('/Users/chen/codeRepository/game_claim_helper/nginx.conf', '/tmp/nginx_game.conf')
        sftp.close()
        
        # 复制到 Nginx 目录
        print("2. 复制配置到 Nginx 目录...")
        run_command(client, "sudo cp /tmp/nginx_game.conf /etc/nginx/conf.d/game_claim_helper.conf", 30)
        
        # 测试配置
        print("3. 测试 Nginx 配置...")
        output = run_command(client, "sudo nginx -t", 30)
        print(output)
        
        # 重载 Nginx
        print("4. 重载 Nginx...")
        run_command(client, "sudo systemctl reload nginx", 30)
        print("Nginx 重载成功!")
        
        print("\n=== 更新完成 ===")
        
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
