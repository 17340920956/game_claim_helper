#!/usr/bin/env python3
"""
检查容器日志
"""
import paramiko

HOST = "101.42.17.176"
USER = "ubuntu"
PASSWORD = "Yang1024@q"

def create_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=60)
    return client

def run_command(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
    stdin.write(PASSWORD + '\n')
    stdin.flush()
    output = stdout.read().decode('utf-8', errors='ignore')
    return output

def main():
    client = None
    try:
        client = create_ssh_client()
        
        print("=== 检查容器日志 ===\n")
        
        # 查看日志
        print("1. 容器日志:")
        output = run_command(client, "sudo docker logs game_claim_helper 2>&1 | tail -50")
        print(output)
        
    except Exception as e:
        print(f"检查失败: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
