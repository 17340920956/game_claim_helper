#!/bin/bash
# MySQL远程连接诊断脚本

echo "=================================="
echo "MySQL远程连接诊断工具"
echo "=================================="
echo ""

# 数据库连接信息
DB_HOST="42.194.167.11"
DB_PORT="3306"
DB_USER="gch_user"
DB_PASS="Gch1024!"
DB_NAME="game_claim_helper"

echo "目标服务器: $DB_HOST:$DB_PORT"
echo "数据库: $DB_NAME"
echo "用户: $DB_USER"
echo ""

# 1. 测试网络连通性
echo "1️⃣  测试网络连通性 (ping)..."
if ping -c 3 $DB_HOST > /dev/null 2>&1; then
    echo "✅ 网络连通正常"
else
    echo "❌ 网络不通，请检查网络或防火墙"
    exit 1
fi
echo ""

# 2. 测试端口连通性
echo "2️⃣  测试MySQL端口 (3306)..."
if command -v nc > /dev/null; then
    if nc -zv $DB_HOST $DB_PORT 2>&1 | grep -q "succeeded\|open"; then
        echo "✅ 端口3306可访问"
    else
        echo "❌ 端口3306不可访问"
        echo "   可能原因：防火墙阻止、MySQL未启动、bind_address限制"
    fi
elif command -v telnet > /dev/null; then
    if timeout 5 bash -c "echo > /dev/tcp/$DB_HOST/$DB_PORT" 2>/dev/null; then
        echo "✅ 端口3306可访问"
    else
        echo "❌ 端口3306不可访问"
    fi
else
    echo "⚠️  未安装nc或telnet，跳过端口测试"
fi
echo ""

# 3. 测试MySQL连接
echo "3️⃣  测试MySQL连接..."
if command -v mysql > /dev/null; then
    if mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p"$DB_PASS" -e "SELECT 1;" 2>/dev/null; then
        echo "✅ MySQL连接成功"
    else
        echo "❌ MySQL连接失败"
        echo ""
        echo "尝试获取详细错误信息..."
        mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p"$DB_PASS" -e "SELECT 1;" 2>&1
    fi
else
    echo "⚠️  本地未安装mysql客户端，使用Python测试..."
    python3 -c "
import pymysql
import sys
try:
    conn = pymysql.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        user='$DB_USER',
        password='$DB_PASS',
        database='$DB_NAME',
        connect_timeout=10
    )
    print('✅ MySQL连接成功')
    conn.close()
except Exception as e:
    print(f'❌ MySQL连接失败: {e}')
    sys.exit(1)
"
fi
echo ""

echo "=================================="
echo "诊断完成"
echo "=================================="
echo ""
echo "如果连接失败，请检查："
echo "1. 远程MySQL服务是否启动"
echo "2. 防火墙是否开放3306端口"
echo "3. MySQL是否允许远程连接"
echo "4. 用户是否有远程访问权限"
