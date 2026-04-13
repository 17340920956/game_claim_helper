#!/usr/bin/env python3
"""
清理 Docker 无用镜像
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
    if error and 'WARNING' not in error and 'Error: No such' not in error:
        print(f"错误: {error[:500]}", file=sys.stderr)
    return output, error

def main():
    print("=== 清理 Docker 无用镜像 ===")
    
    client = create_ssh_client()
    
    try:
        # 1. 查看当前镜像
        print("\n1. 查看当前镜像...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker images", "查看镜像")
        
        # 2. 清理悬空镜像 (dangling images)
        print("\n2. 清理悬空镜像...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker image prune -f", "清理悬空镜像")
        
        # 3. 清理未使用的镜像
        print("\n3. 清理未使用的镜像...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker system prune -f --volumes", "系统清理")
        
        # 4. 查看清理后的镜像
        print("\n4. 查看清理后的镜像...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker images", "查看镜像")
        
        # 5. 查看磁盘使用情况
        print("\n5. 查看 Docker 磁盘使用情况...")
        run_command(client, f"echo '{PASSWORD}' | sudo -S docker system df", "磁盘使用")
        
        print("\n=== 清理完成 ===")
        
    except Exception as e:
        print(f"\n清理失败: {e}", file=sys.stderr)
    finally:
        client.close()

if __name__ == "__main__":
    main()
