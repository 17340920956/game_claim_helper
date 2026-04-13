#!/usr/bin/env python3
"""
修复环境变量，添加 WECHAT_OFFICIAL_URL
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
    print("=== 修复环境变量 ===")
    
    client = create_ssh_client()
    
    try:
        # 检查当前 .env 内容
        print("\n1. 检查当前 .env 文件...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cat {REMOTE_PATH}/.env", "当前配置")
        
        # 添加 WECHAT_OFFICIAL_URL 到 .env
        print("\n2. 添加 WECHAT_OFFICIAL_URL...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S bash -c 'echo \"WECHAT_OFFICIAL_URL=http://yxbot.online\" >> {REMOTE_PATH}/.env'", "添加配置")
        
        # 验证添加成功
        print("\n3. 验证配置...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S grep 'WECHAT_OFFICIAL_URL' {REMOTE_PATH}/.env", "验证配置")
        
        # 重启容器
        print("\n4. 重启容器...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker restart game_claim_helper", "重启容器")
        
        # 等待启动
        print("\n5. 等待容器启动...")
        import time
        time.sleep(5)
        
        # 检查状态
        print("\n6. 检查容器状态...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps | grep game_claim_helper", "检查状态")
        
        print("\n=== 修复完成 ===")
        print("现在微信推送的链接应该是: http://yxbot.online/games/view")
        
    except Exception as e:
        print(f"\n修复失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
