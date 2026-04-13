#!/usr/bin/env python3
"""
更新 Nginx 配置，允许 /games/view HTTP 访问
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
    print("=== 更新 Nginx 配置 ===")
    
    client = create_ssh_client()
    
    try:
        # 创建新的 Nginx 配置
        nginx_config = '''server {
    listen 80;
    server_name yxbot.online;

    # 微信回调接口允许 HTTP 访问（微信服务器验证需要）
    location /wechat/callback {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 游戏展示页面允许 HTTP 访问（微信内打开需要）
    location /games/view {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 其他请求重定向到 HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name yxbot.online;

    ssl_certificate     /etc/nginx/ssl/yxbot.crt;
    ssl_certificate_key /etc/nginx/ssl/yxbot.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
'''
        
        # 写入配置文件
        print("\n1. 更新 Nginx 配置...")
        cmd = f"echo '{PASSWORD}' | sudo -S tee /etc/nginx/sites-available/game_claim_helper"
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
        stdin.write(nginx_config)
        stdin.channel.shutdown_write()
        
        output = stdout.read().decode()
        error = stderr.read().decode()
        if output:
            print(output)
        if error:
            print(f"错误: {error}", file=sys.stderr)
        
        # 测试配置
        print("\n2. 测试 Nginx 配置...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S nginx -t", "配置测试")
        
        # 重载 Nginx
        print("\n3. 重载 Nginx...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S systemctl reload nginx", "重载Nginx")
        
        # 测试 HTTP 访问
        print("\n4. 测试 HTTP 访问 /games/view...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S curl -s -o /dev/null -w '%{{http_code}}' http://localhost/games/view", "HTTP测试")
        
        # 测试外部 HTTP 访问
        print("\n5. 测试外部 HTTP 访问...")
        run_command(client, f"curl -s -o /dev/null -w '%{{http_code}}' http://yxbot.online/games/view", "外部HTTP")
        
    except Exception as e:
        print(f"\n更新失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
