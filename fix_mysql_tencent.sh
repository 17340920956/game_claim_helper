#!/bin/bash
# 腾讯云MySQL远程连接修复脚本
# 请在服务器上运行此脚本

echo "=================================="
echo "腾讯云MySQL远程连接修复工具"
echo "=================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 步骤1: 检查MySQL服务状态
echo -e "${YELLOW}步骤1: 检查MySQL服务状态${NC}"
if systemctl is-active --quiet mysqld || systemctl is-active --quiet mysql; then
    echo -e "${GREEN}✅ MySQL服务正在运行${NC}"
    systemctl status mysqld 2>/dev/null || systemctl status mysql 2>/dev/null
else
    echo -e "${RED}❌ MySQL服务未运行${NC}"
    echo "尝试启动MySQL..."
    systemctl start mysqld 2>/dev/null || systemctl start mysql 2>/dev/null
fi
echo ""

# 步骤2: 检查MySQL监听地址
echo -e "${YELLOW}步骤2: 检查MySQL监听地址${NC}"
echo "当前监听状态:"
netstat -tlnp | grep 3306
echo ""

# 检查是否只监听localhost
if netstat -tlnp | grep 3306 | grep -q "127.0.0.1"; then
    echo -e "${RED}❌ MySQL只监听localhost，需要修改配置${NC}"
    NEED_CONFIG_CHANGE=1
elif netstat -tlnp | grep 3306 | grep -q "0.0.0.0"; then
    echo -e "${GREEN}✅ MySQL监听所有地址${NC}"
    NEED_CONFIG_CHANGE=0
else
    echo -e "${YELLOW}⚠️  无法确定监听状态${NC}"
    NEED_CONFIG_CHANGE=1
fi
echo ""

# 步骤3: 查找并备份MySQL配置文件
echo -e "${YELLOW}步骤3: 查找MySQL配置文件${NC}"
CONFIG_FILE=""
if [ -f "/etc/my.cnf" ]; then
    CONFIG_FILE="/etc/my.cnf"
elif [ -f "/etc/mysql/my.cnf" ]; then
    CONFIG_FILE="/etc/mysql/my.cnf"
elif [ -f "/etc/mysql/mysql.conf.d/mysqld.cnf" ]; then
    CONFIG_FILE="/etc/mysql/mysql.conf.d/mysqld.cnf"
else
    # 尝试查找
    CONFIG_FILE=$(find /etc -name "my.cnf" -o -name "mysqld.cnf" 2>/dev/null | head -n 1)
fi

if [ -z "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ 未找到MySQL配置文件${NC}"
    echo "请手动查找配置文件"
    exit 1
fi

echo -e "${GREEN}✅ 找到配置文件: $CONFIG_FILE${NC}"
echo ""

# 备份配置文件
BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "备份配置文件到: $BACKUP_FILE"
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo ""

# 步骤4: 显示当前配置
echo -e "${YELLOW}步骤4: 当前bind-address配置${NC}"
grep -n "bind-address" "$CONFIG_FILE" 2>/dev/null || echo "未找到bind-address配置"
echo ""

# 步骤5: 修改配置（如果需要）
if [ "$NEED_CONFIG_CHANGE" -eq 1 ]; then
    echo -e "${YELLOW}步骤5: 修改MySQL配置${NC}"
    
    # 检查是否已有bind-address配置
    if grep -q "bind-address" "$CONFIG_FILE"; then
        # 替换现有配置
        sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' "$CONFIG_FILE"
        sed -i 's/^#bind-address.*/bind-address = 0.0.0.0/' "$CONFIG_FILE"
        echo -e "${GREEN}✅ 已修改bind-address为0.0.0.0${NC}"
    else
        # 添加新配置
        # 找到[mysqld]段，在其后添加
        if grep -q "\[mysqld\]" "$CONFIG_FILE"; then
            sed -i '/\[mysqld\]/a bind-address = 0.0.0.0' "$CONFIG_FILE"
            echo -e "${GREEN}✅ 已添加bind-address = 0.0.0.0${NC}"
        else
            # 在文件开头添加
            echo -e "\n[mysqld]\nbind-address = 0.0.0.0" >> "$CONFIG_FILE"
            echo -e "${GREEN}✅ 已添加[mysqld]段和bind-address配置${NC}"
        fi
    fi
    
    # 显示修改后的配置
    echo ""
    echo "修改后的配置:"
    grep -A 2 -B 2 "bind-address" "$CONFIG_FILE"
    echo ""
    
    # 重启MySQL
    echo -e "${YELLOW}重启MySQL服务...${NC}"
    systemctl restart mysqld 2>/dev/null || systemctl restart mysql 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ MySQL重启成功${NC}"
    else
        echo -e "${RED}❌ MySQL重启失败，请检查配置${NC}"
        echo "恢复备份..."
        cp "$BACKUP_FILE" "$CONFIG_FILE"
        systemctl restart mysqld 2>/dev/null || systemctl restart mysql 2>/dev/null
        exit 1
    fi
    
    # 验证监听地址
    sleep 2
    echo ""
    echo "验证监听地址:"
    netstat -tlnp | grep 3306
else
    echo -e "${GREEN}✅ 配置无需修改${NC}"
fi
echo ""

# 步骤6: 检查用户权限
echo -e "${YELLOW}步骤6: 检查MySQL用户权限${NC}"
echo "请输入MySQL root密码:"
mysql -u root -p << 'EOF'
-- 查看gch_user用户的访问权限
SELECT user, host FROM mysql.user WHERE user='gch_user';

-- 如果host是localhost，创建远程访问权限
CREATE USER IF NOT EXISTS 'gch_user'@'%' IDENTIFIED BY 'Gch1024!';
GRANT ALL PRIVILEGES ON game_claim_helper.* TO 'gch_user'@'%';
FLUSH PRIVILEGES;

-- 显示更新后的权限
SELECT user, host FROM mysql.user WHERE user='gch_user';
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 用户权限配置成功${NC}"
else
    echo -e "${RED}❌ 用户权限配置失败${NC}"
fi
echo ""

# 步骤7: 检查防火墙（firewalld）
echo -e "${YELLOW}步骤7: 检查防火墙配置${NC}"
if command -v firewall-cmd &> /dev/null; then
    echo "检测到firewalld防火墙"
    echo "当前开放的端口:"
    firewall-cmd --list-ports
    
    # 检查3306端口是否开放
    if firewall-cmd --list-ports | grep -q "3306/tcp"; then
        echo -e "${GREEN}✅ 3306端口已开放${NC}"
    else
        echo "开放3306端口..."
        firewall-cmd --permanent --add-port=3306/tcp
        firewall-cmd --reload
        echo -e "${GREEN}✅ 3306端口已开放${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  未检测到firewalld，跳过防火墙配置${NC}"
fi
echo ""

# 步骤8: 提示检查腾讯云安全组
echo -e "${YELLOW}步骤8: 腾讯云安全组配置${NC}"
echo "请确保在腾讯云控制台配置了安全组规则："
echo "1. 登录腾讯云控制台"
echo "2. 进入云服务器实例详情"
echo "3. 点击'安全组'标签"
echo "4. 点击'配置规则'"
echo "5. 添加入站规则:"
echo "   - 类型: 自定义"
echo "   - 来源: 0.0.0.0/0 (或指定你的IP)"
echo "   - 协议端口: TCP:3306"
echo "   - 策略: 允许"
echo ""

# 步骤9: 测试连接
echo -e "${YELLOW}步骤9: 本地测试连接${NC}"
echo "尝试本地连接..."
mysql -u gch_user -p'Gch1024!' -h 127.0.0.1 -e "SELECT 'Connection successful!' as status;"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 本地连接成功${NC}"
else
    echo -e "${RED}❌ 本地连接失败${NC}"
fi
echo ""

# 完成
echo "=================================="
echo -e "${GREEN}修复完成！${NC}"
echo "=================================="
echo ""
echo "请在本地机器运行以下命令测试连接:"
echo "python3 -c \"import pymysql; conn = pymysql.connect(host='42.194.167.11', port=3306, user='gch_user', password='Gch1024!', database='game_claim_helper'); print('✅ 连接成功!'); conn.close()\""
echo ""
echo "如果仍然失败，请检查:"
echo "1. 腾讯云安全组是否开放3306端口"
echo "2. MySQL错误日志: tail -f /var/log/mysqld.log"
