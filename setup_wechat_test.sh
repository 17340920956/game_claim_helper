#!/bin/bash

echo "================================"
echo "微信测试号配置助手"
echo "================================"
echo ""

echo "步骤1: 请访问以下地址申请测试号"
echo "https://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login"
echo ""
echo "扫码登录后，请记录以下信息："
echo "  - appID"
echo "  - appsecret"
echo ""

echo "步骤2: 启动内网穿透"
echo "如果使用 ngrok:"
echo "  ./ngrok http 8000"
echo ""
echo "如果使用 cpolar:"
echo "  cpolar http 8000"
echo ""
echo "记录生成的 HTTPS URL，例如: https://abc123.ngrok.io"
echo ""

echo "步骤3: 配置环境变量"
echo "请输入测试号信息："
read -p "appID: " appid
read -p "appsecret: " secret
read -p "Token (自定义，例如: mytoken123): " token
read -p "内网穿透URL (例如: https://abc123.ngrok.io): " base_url

cat > .env << EOF
DATABASE_URL=mysql+pymysql://gch:Gch1024!@42.194.176.11:3306/game_claim_helper
REDIS_URL=redis://localhost:6379/0

EPIC_FREE_GAMES_URL=https://store.epicgames.com/en-US/free-games

WECHAT_OFFICIAL_APPID=$appid
WECHAT_OFFICIAL_SECRET=$secret
WECHAT_OFFICIAL_TOKEN=$token
WECHAT_OFFICIAL_AES_KEY=

SCHEDULER_TIMEZONE=Asia/Shanghai

SECRET_KEY=test-secret-key-12345
ADMIN_API_KEY=admin-key-12345
BASE_URL=$base_url
EOF

echo ""
echo "配置已保存到 .env 文件"
echo ""

echo "步骤4: 在测试号页面配置服务器"
echo "URL: ${base_url}/wechat/callback"
echo "Token: $token"
echo ""
echo "请确保应用正在运行，然后在测试号页面点击提交"
echo ""

echo "步骤5: 启动应用"
echo "python run.py"
echo ""

echo "配置完成！"
