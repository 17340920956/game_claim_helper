#!/usr/bin/env python3
"""
手动部署 - 分步执行
"""
import paramiko
import time

HOST = "101.42.17.176"
USER = "ubuntu"
PASSWORD = "Yang1024@q"

def create_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=60)
    return client

def run_command(client, cmd, timeout=300):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    output = stdout.read().decode('utf-8', errors='ignore')
    return output

def main():
    client = None
    try:
        client = create_ssh_client()
        
        print("=== 手动部署 ===\n")
        
        # 上传脚本
        print("1. 上传构建脚本...")
        sftp = client.open_sftp()
        sftp.put('/Users/chen/codeRepository/game_claim_helper/build_and_run.sh', '/tmp/build_and_run.sh')
        sftp.close()
        run_command(client, "chmod +x /tmp/build_and_run.sh")
        print("完成")
        
        # 执行构建和启动
        print("\n2. 执行构建和启动（约5-10分钟）...")
        print("   正在构建镜像，请耐心等待...")
        output = run_command(client, "cd /tmp && sudo bash build_and_run.sh 2>&1", timeout=600)
        print(output[-2000:] if len(output) > 2000 else output)
        
        print("\n=== 部署完成 ===")
        
    except Exception as e:
        print(f"\n部署失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
