#!/usr/bin/env python3
"""
修复 Nginx 配置
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
    print("=== 修复 Nginx 配置 ===")
    
    client = create_ssh_client()
    
    try:
        # 先备份并删除损坏的配置
        print("\n1. 备份并删除损坏配置...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cp /etc/nginx/sites-available/game_claim_helper /tmp/nginx_backup 2>/dev/null; echo '{PASSWORD}' | sudo -S rm -f /etc/nginx/sites-enabled/game_claim_helper", "备份删除")
        
        # 创建新的配置文件
        print("\n2. 创建新配置...")
        config_lines = [
            "server {",
            "    listen 80;",
            "    server_name yxbot.online;",
            "",
            "    location /wechat/callback {",
            "        proxy_pass http://127.0.0.1:8000;",
            "        proxy_set_header Host $host;",
            "        proxy_set_header X-Real-IP $remote_addr;",
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "        proxy_set_header X-Forwarded-Proto $scheme;",
            "    }",
            "",
            "    location /games/view {",
            "        proxy_pass http://127.0.0.1:8000;",
            "        proxy_set_header Host $host;",
            "        proxy_set_header X-Real-IP $remote_addr;",
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "        proxy_set_header X-Forwarded-Proto $scheme;",
            "    }",
            "",
            "    location / {",
            "        return 301 https://$host$request_uri;",
            "    }",
            "}",
            "",
            "server {",
            "    listen 443 ssl;",
            "    server_name yxbot.online;",
            "",
            "    ssl_certificate /etc/nginx/ssl/yxbot.crt;",
            "    ssl_certificate_key /etc/nginx/ssl/yxbot.key;",
            "",
            "    ssl_protocols TLSv1.2 TLSv1.3;",
            "    ssl_ciphers HIGH:!aNULL:!MD5;",
            "",
            "    client_max_body_size 10M;",
            "",
            "    location / {",
            "        proxy_pass http://127.0.0.1:8000;",
            "        proxy_set_header Host $host;",
            "        proxy_set_header X-Real-IP $remote_addr;",
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "        proxy_set_header X-Forwarded-Proto $scheme;",
            "        proxy_read_timeout 300;",
            "        proxy_connect_timeout 300;",
            "        proxy_send_timeout 300;",
            "    }",
            "}"
        ]
        
        config_content = "\\n".join(config_lines)
        run_command(client, f"echo '{PASSWORD}' | sudo -S bash -c 'cat > /etc/nginx/sites-available/game_claim_helper' << 'EOF'\n{config_content}\nEOF", "写入配置")
        
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
        
    except Exception as e:
        print(f"\n修复失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
