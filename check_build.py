#!/usr/bin/env python3
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
        
        print("=== 检查构建状态 ===\n")
        
        # 检查构建日志
        print("1. 构建日志 (最后50行):")
        output = run_command(client, "tail -50 /tmp/build.log")
        print(output)
        
        # 检查镜像是否存在
        print("\n2. 镜像列表:")
        output = run_command(client, "sudo docker images | grep game_claim_helper")
        print(output if output else "  无镜像")
        
        # 检查是否有构建进程在运行
        print("\n3. 构建进程:")
        output = run_command(client, "ps aux | grep docker | grep -v grep")
        print(output if output else "  无构建进程")
        
    except Exception as e:
        print(f"检查失败: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
