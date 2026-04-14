#!/usr/bin/env python3
"""
最终部署脚本
"""
import paramiko
import subprocess

HOST = "101.42.17.176"
USER = "ubuntu"
PASSWORD = "Yang1024@q"

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
        # 打包代码
        print("=== 打包代码 ===")
        subprocess.run(["git", "archive", "-o", "/tmp/game_claim_helper.tar.gz", "HEAD"], check=True)
        print("✓ 打包完成")
        
        client = create_ssh_client()
        
        # 上传代码
        print("\n=== 上传代码 ===")
        sftp = client.open_sftp()
        sftp.put('/tmp/game_claim_helper.tar.gz', '/tmp/game_claim_helper.tar.gz')
        sftp.close()
        print("✓ 上传完成")
        
        # 上传部署脚本
        print("\n=== 上传部署脚本 ===")
        sftp = client.open_sftp()
        sftp.put('/Users/chen/codeRepository/game_claim_helper/cleanup_and_deploy.sh', '/tmp/cleanup_and_deploy.sh')
        sftp.close()
        run_command(client, "chmod +x /tmp/cleanup_and_deploy.sh")
        print("✓ 上传完成")
        
        # 执行部署
        print("\n=== 执行部署（约5-10分钟）===")
        output = run_command(client, "sudo bash /tmp/cleanup_and_deploy.sh", timeout=600)
        print(output[-3000:] if len(output) > 3000 else output)
        
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
