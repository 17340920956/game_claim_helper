#!/usr/bin/env python3
"""
部署脚本 - 上传代码并在服务器上执行部署
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
    client.connect(HOST, username=USER, password=PASSWORD, timeout=60)
    return client

def run_command(client, cmd, timeout=600):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    output = stdout.read().decode('utf-8', errors='ignore')
    return output

def main():
    client = None
    try:
        client = create_ssh_client()
        
        print("=== 开始部署 ===\n")
        
        # 1. 上传代码包
        print("1. 上传代码包...")
        sftp = client.open_sftp()
        sftp.put('/tmp/game_claim_helper.tar.gz', '/tmp/game_claim_helper.tar.gz')
        sftp.close()
        print("上传完成!")
        
        # 2. 上传部署脚本
        print("\n2. 上传部署脚本...")
        sftp = client.open_sftp()
        sftp.put('/Users/chen/codeRepository/game_claim_helper/remote_deploy.sh', '/tmp/remote_deploy.sh')
        sftp.close()
        run_command(client, "chmod +x /tmp/remote_deploy.sh")
        print("上传完成!")
        
        # 3. 在服务器上执行部署
        print("\n3. 在服务器上执行部署（约5-10分钟）...")
        output = run_command(client, "cd /tmp && sudo bash remote_deploy.sh", timeout=600)
        print(output)
        
        print("\n=== 部署完成 ===")
        print("访问地址: https://yxbot.online/wechat/callback")
        
    except Exception as e:
        print(f"\n部署失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
