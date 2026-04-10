# MySQL远程连接修复指南

## 问题诊断

已确认连接失败：`42.194.167.11:3306`

错误信息：`Lost connection to MySQL server during query`

## 远程服务器检查步骤

### 1️⃣ 登录远程服务器

```bash
ssh user@42.194.167.11
```

### 2️⃣ 检查MySQL服务状态

```bash
# CentOS/RHEL
systemctl status mysqld
# 或
systemctl status mysql

# Ubuntu/Debian
systemctl status mysql

# 如果未启动，启动服务
systemctl start mysqld
# 或
systemctl start mysql
```

### 3️⃣ 检查MySQL监听地址

```bash
# 查看MySQL监听端口
netstat -tlnp | grep 3306

# 期望输出：
# tcp  0  0  0.0.0.0:3306  0.0.0.0:*  LISTEN  pid/mysqld
# 或
# tcp6 0  0  :::3306       :::*       LISTEN  pid/mysqld

# 如果只监听 127.0.0.1:3306，需要修改配置
```

### 4️⃣ 检查MySQL配置文件

```bash
# 查找配置文件
find /etc -name my.cnf 2>/dev/null
find /etc -name mysqld.cnf 2>/dev/null

# 常见位置：
# - /etc/my.cnf
# - /etc/mysql/my.cnf
# - /etc/mysql/mysql.conf.d/mysqld.cnf

# 编辑配置文件
sudo vi /etc/my.cnf
# 或
sudo vi /etc/mysql/mysql.conf.d/mysqld.cnf
```

**修改 `bind-address` 配置：**

```ini
[mysqld]
# 允许所有IP连接（推荐）
bind-address = 0.0.0.0

# 或只允许特定IP
# bind-address = 127.0.0.1  # 本地
# bind-address = 42.194.167.11  # 本机IP
```

### 5️⃣ 检查防火墙

#### CentOS/RHEL (firewalld)

```bash
# 查看防火墙状态
firewall-cmd --state

# 查看开放的端口
firewall-cmd --list-ports

# 开放3306端口
firewall-cmd --permanent --add-port=3306/tcp
firewall-cmd --reload

# 或开放给特定IP
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="你的本地IP" port protocol="tcp" port="3306" accept'
firewall-cmd --reload
```

#### Ubuntu/Debian (ufw)

```bash
# 查看防火墙状态
ufw status

# 开放3306端口
ufw allow 3306/tcp

# 或开放给特定IP
ufw allow from 你的本地IP to any port 3306
```

#### iptables

```bash
# 查看规则
iptables -L -n | grep 3306

# 开放3306端口
iptables -I INPUT -p tcp --dport 3306 -j ACCEPT
service iptables save  # CentOS 6
# 或
iptables-save > /etc/iptables/rules.v4  # Ubuntu/Debian
```

### 6️⃣ 检查用户权限

```bash
# 登录MySQL
mysql -u root -p

# 查看用户权限
SELECT user, host FROM mysql.user WHERE user='gch_user';

# 期望输出：
# +----------+------+
# | user     | host |
# +----------+------+
# | gch_user | %    |  # % 表示允许任何主机
# +----------+------+

# 如果 host 是 localhost，需要创建远程访问权限
CREATE USER 'gch_user'@'%' IDENTIFIED BY 'Gch1024!';
GRANT ALL PRIVILEGES ON game_claim_helper.* TO 'gch_user'@'%';
FLUSH PRIVILEGES;

# 或修改现有用户
UPDATE mysql.user SET host='%' WHERE user='gch_user';
FLUSH PRIVILEGES;
```

### 7️⃣ 重启MySQL服务

```bash
# 修改配置后重启
systemctl restart mysqld
# 或
systemctl restart mysql

# 检查服务状态
systemctl status mysqld
```

### 8️⃣ 云服务商安全组（如果是云服务器）

**腾讯云：**
1. 登录腾讯云控制台
2. 进入云服务器实例详情
3. 点击"安全组"
4. 添加入站规则：
   - 协议：TCP
   - 端口：3306
   - 来源：0.0.0.0/0（或指定IP）

**阿里云：**
1. 登录阿里云控制台
2. 进入ECS实例详情
3. 点击"安全组"
4. 配置规则 → 添加安全组规则
   - 端口范围：3306/3306
   - 授权对象：0.0.0.0/0

**AWS：**
1. 登录AWS控制台
2. EC2 → Security Groups
3. Edit inbound rules
4. Add Rule: MySQL (3306)

## 验证修复

在本地机器运行诊断脚本：

```bash
bash diagnose_mysql.sh
```

或在本地测试连接：

```bash
python3 -c "
import pymysql
conn = pymysql.connect(
    host='42.194.167.11',
    port=3306,
    user='gch_user',
    password='Gch1024!',
    database='game_claim_helper'
)
print('✅ 连接成功！')
conn.close()
"
```

## 常见问题

### 问题1：ERROR 2003 (HY000): Can't connect to MySQL server

**原因：** 防火墙或bind-address限制

**解决：** 检查防火墙和MySQL配置

### 问题2：ERROR 1045 (28000): Access denied for user

**原因：** 用户权限不足

**解决：** 检查用户权限，确保host为'%'或包含客户端IP

### 问题3：ERROR 2013 (HY000): Lost connection to MySQL server

**原因：** bind-address只监听localhost或防火墙

**解决：** 修改bind-address为0.0.0.0，开放防火墙

## 安全建议

⚠️ **生产环境安全建议：**

1. **不要对所有IP开放**：
   ```bash
   # 只允许特定IP访问
   firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="你的IP" port protocol="tcp" port="3306" accept'
   ```

2. **使用强密码**：
   ```sql
   ALTER USER 'gch_user'@'%' IDENTIFIED BY '更复杂的密码!';
   ```

3. **限制用户权限**：
   ```sql
   -- 只授予必要权限
   GRANT SELECT, INSERT, UPDATE, DELETE ON game_claim_helper.* TO 'gch_user'@'%';
   ```

4. **启用SSL连接**（可选）：
   ```sql
   ALTER USER 'gch_user'@'%' REQUIRE SSL;
   ```

## 需要帮助？

如果以上步骤无法解决问题，请提供：

1. MySQL服务状态：`systemctl status mysqld`
2. MySQL监听端口：`netstat -tlnp | grep 3306`
3. MySQL配置文件：`cat /etc/my.cnf`
4. 用户权限：`SELECT user, host FROM mysql.user;`
5. 防火墙规则：`firewall-cmd --list-all`
