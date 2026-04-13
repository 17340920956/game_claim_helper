#!/usr/bin/env python3
"""
检查并修复环境变量
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
    print("=== 检查并修复环境变量 ===")
    
    client = create_ssh_client()
    
    try:
        # 检查当前 .env
        print("\n1. 检查当前 .env 文件...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cat {REMOTE_PATH}/.env", "当前配置")
        
        # 检查 WECHAT_OFFICIAL_URL
        print("\n2. 检查 WECHAT_OFFICIAL_URL...")
        output, _ = run_command(client, f"echo '{PASSWORD}' | sudo -S grep 'WECHAT_OFFICIAL_URL' {REMOTE_PATH}/.env", "检查URL")
        
        # 如果没有设置或设置错误，修复它
        if "WECHAT_OFFICIAL_URL" not in output or "localhost" in output:
            print("\n3. 修复 WECHAT_OFFICIAL_URL...")
            # 删除旧的配置行
            run_command(client, f"echo '{PASSWORD}' | sudo -S sed -i '/WECHAT_OFFICIAL_URL/d' {REMOTE_PATH}/.env", "删除旧配置")
            # 添加正确的配置
            run_command(client, f"echo '{PASSWORD}' | sudo -S bash -c 'echo \"WECHAT_OFFICIAL_URL=http://yxbot.online\" >> {REMOTE_PATH}/.env'", "添加新配置")
        
        # 验证
        print("\n4. 验证配置...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S grep 'WECHAT_OFFICIAL_URL' {REMOTE_PATH}/.env", "验证配置")
        
        print("\n=== 检查完成 ===")
        
    except Exception as e:
        print(f"\n检查失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
