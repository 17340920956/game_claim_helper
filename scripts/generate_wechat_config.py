#!/usr/bin/env python3
"""
生成微信公众号配置所需的 Token 和 EncodingAESKey
"""
import secrets
import string

def generate_token(length=32):
    """生成随机 Token（3-32字符）"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_aes_key():
    """生成 43 位 EncodingAESKey"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(43))

if __name__ == "__main__":
    print("微信公众号配置生成器")
    print("=" * 60)
    
    token = generate_token(32)
    aes_key = generate_aes_key()
    
    print(f"\n生成的配置信息：\n")
    print(f"Token: {token}")
    print(f"EncodingAESKey: {aes_key}")
    
    print("\n" + "=" * 60)
    print("请将以上信息复制到微信公众平台服务器配置中")
    print("=" * 60)
