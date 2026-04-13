#!/usr/bin/env python3
"""
检查部署状态
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
    error = stderr.read().decode('utf-8', errors='ignore')
    return output, error

def main():
    client = None
    try:
        client = create_ssh_client()
        
        print("=== 检查部署状态 ===\n")
        
        # 1. 检查容器状态
        print("1. Docker容器状态:")
        output, _ = run_command(client, f"echo '{PASSWORD}' | sudo -S docker ps -a | grep game_claim")
        print(output if output else "  无容器")
        
        # 2. 检查后台进程
        print("\n2. 后台部署进程:")
        output, _ = run_command(client, "ps aux | grep deploy_bg | grep -v grep")
        print(output if output else "  无运行中的部署进程")
        
        # 3. 查看部署日志
        print("\n3. 部署日志 (最后50行):")
        output, _ = run_command(client, "tail -50 /tmp/deploy_*.log 2>/dev/null || echo '无日志文件'")
        print(output)
        
        # 4. 查看nohup日志
        print("\n4. Nohup日志:")
        output, _ = run_command(client, "cat /tmp/deploy_nohup.log 2>/dev/null || echo '无nohup日志'")
        print(output[-2000:] if len(output) > 2000 else output)
        
    except Exception as e:
        print(f"检查失败: {e}", file=sys.stderr)
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
