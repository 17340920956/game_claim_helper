#!/usr/bin/env python3
"""
检查微信公众号接口状态
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
        
        print("=== 检查微信公众号接口 ===\n")
        
        # 1. 检查容器状态
        print("1. 容器状态:")
        output = run_command(client, "sudo docker ps | grep game_claim_helper")
        print(output if output else "  容器未运行")
        
        # 2. 测试微信回调接口
        print("\n2. 测试微信回调接口 (GET):")
        output = run_command(client, "curl -s 'http://localhost:8000/wechat/callback?signature=test&timestamp=123456&nonce=test&echostr=hello' 2>&1")
        print(f"  响应: {output}")
        
        # 3. 测试微信回调接口 (POST)
        print("\n3. 测试微信回调接口 (POST):")
        xml_data = '<xml><ToUserName>test</ToUserName><FromUserName>user</FromUserName><CreateTime>123456</CreateTime><MsgType>text</MsgType><Content>游戏</Content></xml>'
        output = run_command(client, f"curl -s -X POST -H 'Content-Type: application/xml' -d '{xml_data}' 'http://localhost:8000/wechat/callback?signature=test&timestamp=123456&nonce=test' 2>&1")
        print(f"  响应: {output[:500] if len(output) > 500 else output}")
        
        # 4. 查看容器日志
        print("\n4. 容器日志 (最后30行):")
        output = run_command(client, "sudo docker logs --tail 30 game_claim_helper 2>&1")
        print(output)
        
        # 5. 检查Nginx配置
        print("\n5. Nginx配置检查:")
        output = run_command(client, "sudo nginx -t 2>&1")
        print(output)
        
    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
