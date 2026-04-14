#!/usr/bin/env python3
"""
部署脚本 - 简化版
"""
import paramiko
import subprocess
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

        # 执行部署
        print("\n=== 执行部署 ===")
        deploy_script = f"""
cd {REMOTE_PATH}
sudo docker stop game_claim_helper 2>/dev/null || true
sudo docker rm game_claim_helper 2>/dev/null || true
sudo tar xzf /tmp/game_claim_helper.tar.gz --overwrite
sudo docker build -t game_claim_helper:latest . 2>&1 | tail -20
sudo docker run -d --name game_claim_helper --network host --env-file {REMOTE_PATH}/.env -v /var/log/game_claim_helper:/app/logs --restart unless-stopped game_claim_helper:latest
sleep 3
sudo docker ps | grep game_claim_helper
sudo docker logs --tail 10 game_claim_helper
"""
        output = run_command(client, deploy_script, timeout=600)
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
