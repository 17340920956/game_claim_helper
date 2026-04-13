#!/usr/bin/env python3
"""
修复 .env 文件格式
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
    print("=== 修复 .env 文件格式 ===")
    
    client = create_ssh_client()
    
    try:
        # 修复格式问题 - 删除错误的行并重新添加
        print("\n1. 修复 BASE_URL 和 WECHAT_OFFICIAL_URL...")
        
        # 删除有问题的行
        run_command(client, f"echo '{PASSWORD}' | sudo -S sed -i '/^BASE_URL=https:\/\/yxbot.onlineWECHAT/d' {REMOTE_PATH}/.env")
        
        # 检查是否还有 WECHAT_OFFICIAL_URL
        output, _ = run_command(client, f"echo '{PASSWORD}' | sudo -S grep '^WECHAT_OFFICIAL_URL' {REMOTE_PATH}/.env")
        
        if "WECHAT_OFFICIAL_URL" not in output:
            print("\n2. 添加正确的 WECHAT_OFFICIAL_URL...")
            run_command(client, f"echo '{PASSWORD}' | sudo -S bash -c 'echo \"WECHAT_OFFICIAL_URL=http://yxbot.online\" >> {REMOTE_PATH}/.env'")
        
        # 检查 BASE_URL
        output, _ = run_command(client, f"echo '{PASSWORD}' | sudo -S grep '^BASE_URL' {REMOTE_PATH}/.env")
        if "BASE_URL" not in output:
            print("\n3. 添加正确的 BASE_URL...")
            run_command(client, f"echo '{PASSWORD}' | sudo -S bash -c 'echo \"BASE_URL=https://yxbot.online\" >> {REMOTE_PATH}/.env'")
        
        # 验证修复结果
        print("\n4. 验证修复结果...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S cat {REMOTE_PATH}/.env | tail -10")
        
        print("\n=== 修复完成 ===")
        
    except Exception as e:
        print(f"\n修复失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
