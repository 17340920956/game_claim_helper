# 云服务部署指南

本文档详细说明如何将 Game Claim Helper 部署到云服务器。

## 目录

- [服务器要求](#服务器要求)
- [部署方式选择](#部署方式选择)
- [Docker 部署（推荐）](#docker-部署推荐)
- [手动部署](#手动部署)
- [Nginx 配置](#nginx-配置)
- [域名与 SSL](#域名与-ssl)
- [微信公众号配置](#微信公众号配置)
- [监控与日志](#监控与日志)
- [故障排查](#故障排查)

## 服务器要求

### 最低配置

- **CPU**: 1 核
- **内存**: 2 GB
- **硬盘**: 20 GB
- **带宽**: 1 Mbps

### 推荐配置

- **CPU**: 2 核
- **内存**: 4 GB
- **硬盘**: 40 GB SSD
- **带宽**: 5 Mbps

### 操作系统

- Ubuntu 20.04 LTS / 22.04 LTS
- CentOS 7+ / 8+
- Debian 10+

### 必需软件

- Docker 20.10+
- Docker Compose 2.0+
- Git
- Nginx（用于反向代理）

## 部署方式选择

### 方式一：Docker 部署（推荐）

优点：
- 环境隔离，依赖管理简单
- 一键启动，易于维护
- 支持快速回滚

### 方式二：手动部署

优点：
- 更灵活的配置
- 便于调试和开发

## Docker 部署（推荐）

### 1. 安装 Docker

**Ubuntu/Debian:**
```bash
# 更新包索引
sudo apt update

# 安装依赖
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# 添加 Docker 官方 GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker compose version
```

**CentOS:**
```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker compose version
```

### 2. 准备项目

```bash
# 创建项目目录
mkdir -p /opt/game_claim_helper
cd /opt/game_claim_helper

# 克隆代码
git clone https://github.com/17340920956/game_claim_helper.git .

# 或者上传代码
# scp -r ./game_claim_helper user@server:/opt/
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
```

**.env 文件内容：**
```bash
# 数据库配置
DATABASE_URL=mysql+pymysql://gch:YourPassword123!@mysql:3306/game_claim_helper

# Redis 配置
REDIS_URL=redis://:YourRedisPassword@redis:6379/0

# Epic 配置
EPIC_FREE_GAMES_URL=https://store.epicgames.com/en-US/free-games

# 微信公众号配置
WECHAT_OFFICIAL_APPID=wx1234567890abcdef
WECHAT_OFFICIAL_SECRET=your_secret_key_here
WECHAT_OFFICIAL_TOKEN=your_token_here
WECHAT_OFFICIAL_AES_KEY=your_aes_key_here
WECHAT_OFFICIAL_TEMPLATE_ID=your_template_id_here

# 调度器时区
SCHEDULER_TIMEZONE=Asia/Shanghai

# 安全配置
SECRET_KEY=your-secret-key-change-me
ADMIN_API_KEY=your-admin-api-key
BASE_URL=https://your-domain.com
```

### 4. 创建 Docker 网络

```bash
docker network create game_claim_network
```

### 5. 部署 MySQL

```bash
# 创建 MySQL 容器
docker run -d \
  --name mysql \
  --network game_claim_network \
  -e MYSQL_ROOT_PASSWORD=RootPassword123! \
  -e MYSQL_DATABASE=game_claim_helper \
  -e MYSQL_USER=gch \
  -e MYSQL_PASSWORD=YourPassword123! \
  -v mysql_data:/var/lib/mysql \
  -p 3306:3306 \
  mysql:8.0 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci

# 等待 MySQL 启动（约 30 秒）
sleep 30

# 验证 MySQL
docker exec -it mysql mysql -ugch -pYourPassword123! -e "SELECT 1;"
```

### 6. 部署 Redis

```bash
# 创建 Redis 容器
docker run -d \
  --name redis \
  --network game_claim_network \
  -v redis_data:/data \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --requirepass YourRedisPassword

# 验证 Redis
docker exec -it redis redis-cli -a YourRedisPassword ping
```

### 7. 部署应用

```bash
# 构建镜像
docker build -t game_claim_helper:latest .

# 运行容器
docker run -d \
  --name game_claim_helper \
  --network game_claim_network \
  --env-file .env \
  -p 8000:8000 \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  game_claim_helper:latest

# 查看日志
docker logs -f game_claim_helper
```

### 8. 使用 Docker Compose（更简单）

创建 `docker-compose.prod.yml` 文件：

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: gch_mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: game_claim_helper
      MYSQL_USER: gch
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    networks:
      - gch_network

  redis:
    image: redis:7-alpine
    container_name: gch_redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - gch_network

  app:
    image: game_claim_helper:latest
    container_name: gch_app
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: mysql+pymysql://gch:${MYSQL_PASSWORD}@mysql:3306/game_claim_helper
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    depends_on:
      - mysql
      - redis
    networks:
      - gch_network

volumes:
  mysql_data:
  redis_data:

networks:
  gch_network:
    driver: bridge
```

运行：
```bash
# 构建镜像
docker build -t game_claim_helper:latest .

# 启动所有服务
docker compose -f docker-compose.prod.yml up -d

# 查看状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f app
```

## 手动部署

### 1. 安装 Python

```bash
# Ubuntu
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3-pip

# CentOS
sudo yum install -y python39 python39-pip
```

### 2. 安装 MySQL

```bash
# Ubuntu
sudo apt install -y mysql-server mysql-client
sudo systemctl start mysql
sudo mysql_secure_installation

# 创建数据库和用户
mysql -u root -p
```

```sql
CREATE DATABASE game_claim_helper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'gch'@'localhost' IDENTIFIED BY 'YourPassword123!';
GRANT ALL PRIVILEGES ON game_claim_helper.* TO 'gch'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 安装 Redis

```bash
# Ubuntu
sudo apt install -y redis-server
sudo systemctl start redis
sudo systemctl enable redis

# 配置密码
sudo vim /etc/redis/redis.conf
# 取消注释 requirepass 并设置密码
# requirepass YourRedisPassword

sudo systemctl restart redis
```

### 4. 部署应用

```bash
# 创建应用目录
sudo mkdir -p /opt/game_claim_helper
cd /opt/game_claim_helper

# 克隆代码
git clone https://github.com/17340920956/game_claim_helper.git .

# 创建虚拟环境
python3.9 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
vim .env

# 启动应用
python run.py
```

### 5. 使用 Systemd 管理服务

创建服务文件：
```bash
sudo vim /etc/systemd/system/game_claim_helper.service
```

内容：
```ini
[Unit]
Description=Game Claim Helper
After=network.target mysql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/game_claim_helper
Environment="PATH=/opt/game_claim_helper/venv/bin"
ExecStart=/opt/game_claim_helper/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl start game_claim_helper
sudo systemctl enable game_claim_helper
sudo systemctl status game_claim_helper
```

## Nginx 配置

### 1. 安装 Nginx

```bash
# Ubuntu
sudo apt install -y nginx

# CentOS
sudo yum install -y nginx

# 启动 Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 2. 配置反向代理

创建配置文件：
```bash
sudo vim /etc/nginx/sites-available/game_claim_helper
```

内容：
```nginx
upstream game_claim_helper {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书配置（使用 Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 日志
    access_log /var/log/nginx/game_claim_helper_access.log;
    error_log /var/log/nginx/game_claim_helper_error.log;

    # 微信公众号验证文件
    location ~ ^/MP_verify_.*\.txt$ {
        root /opt/game_claim_helper;
        try_files /$uri =404;
    }

    # 微信回调
    location /wechat/ {
        proxy_pass http://game_claim_helper;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API 接口
    location / {
        proxy_pass http://game_claim_helper;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 健康检查
    location /health {
        proxy_pass http://game_claim_helper;
        access_log off;
    }
}
```

启用配置：
```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/game_claim_helper /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

## 域名与 SSL

### 1. 域名解析

在域名服务商处添加 A 记录：
```
类型: A
主机记录: @
记录值: 你的服务器 IP
```

### 2. 安装 Certbot

```bash
# Ubuntu
sudo apt install -y certbot python3-certbot-nginx

# CentOS
sudo yum install -y certbot python3-certbot-nginx
```

### 3. 申请 SSL 证书

```bash
# 申请证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

Certbot 会自动修改 Nginx 配置，添加 SSL 相关设置。

## 微信公众号配置

### 1. 配置服务器

登录微信公众平台 -> 设置与开发 -> 基本配置 -> 服务器配置

- **URL**: `https://your-domain.com/wechat/callback`
- **Token**: 与 .env 中的 WECHAT_OFFICIAL_TOKEN 一致
- **EncodingAESKey**: 随机生成或自定义
- **消息加解密方式**: 安全模式（推荐）

### 2. 上传验证文件

下载微信提供的验证文件（MP_verify_xxx.txt），放到项目根目录：
```bash
# 文件位置
/opt/game_claim_helper/MP_verify_xxx.txt
```

### 3. 配置模板消息

设置与开发 -> 功能 -> 模板消息

创建模板，例如：
```
{{first.DATA}}
游戏名称：{{keyword1.DATA}}
活动时间：{{keyword2.DATA}}
{{remark.DATA}}
```

获取模板 ID，配置到 .env 文件：
```bash
WECHAT_OFFICIAL_TEMPLATE_ID=your_template_id
```

### 4. 配置 IP 白名单

设置与开发 -> 基本配置 -> IP白名单

添加你的服务器 IP 地址。

## 监控与日志

### 1. 应用日志

日志文件位置：
```bash
/opt/game_claim_helper/logs/
├── app.log      # 应用日志
└── error.log    # 错误日志
```

查看日志：
```bash
# 实时查看
tail -f logs/app.log

# 查看错误
tail -f logs/error.log

# 搜索特定内容
grep "ERROR" logs/app.log
```

### 2. Docker 日志

```bash
# 查看容器日志
docker logs -f game_claim_helper

# 查看最近 100 行
docker logs --tail 100 game_claim_helper

# 查看指定时间段
docker logs --since 2024-01-01 game_claim_helper
```

### 3. 系统监控

安装监控工具：
```bash
# 安装 htop
sudo apt install -y htop

# 安装 iotop
sudo apt install -y iotop

# 查看系统状态
htop
```

### 4. 日志轮转

创建日志轮转配置：
```bash
sudo vim /etc/logrotate.d/game_claim_helper
```

内容：
```
/opt/game_claim_helper/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload game_claim_helper > /dev/null 2>&1 || true
    endscript
}
```

## 故障排查

### 1. 容器无法启动

```bash
# 查看容器状态
docker ps -a

# 查看日志
docker logs game_claim_helper

# 检查配置
docker exec -it game_claim_helper env

# 进入容器调试
docker exec -it game_claim_helper /bin/bash
```

### 2. 数据库连接失败

```bash
# 检查 MySQL 容器
docker ps | grep mysql
docker logs mysql

# 测试连接
docker exec -it mysql mysql -ugch -p

# 检查网络
docker network inspect game_claim_network
```

### 3. Redis 连接失败

```bash
# 检查 Redis 容器
docker ps | grep redis
docker logs redis

# 测试连接
docker exec -it redis redis-cli -a YourRedisPassword ping
```

### 4. 微信推送失败

```bash
# 检查 access_token
curl -X GET "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=YOUR_APPID&secret=YOUR_SECRET"

# 检查模板消息
curl -X POST "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"touser":"OPENID","template_id":"TEMPLATE_ID","data":{}}'

# 查看应用日志
tail -f logs/app.log | grep "wechat"
```

### 5. 定时任务不执行

```bash
# 检查调度器状态
curl http://localhost:8000/health

# 查看调度器日志
tail -f logs/app.log | grep "scheduler"

# 手动触发任务
curl -X POST http://localhost:8000/api/v1/tasks/trigger \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 6. 性能问题

```bash
# 查看资源使用
docker stats

# 查看进程
ps aux | grep python

# 查看连接数
netstat -an | grep :8000 | wc -l

# 查看数据库连接
docker exec -it mysql mysql -e "SHOW PROCESSLIST;"
```

## 备份与恢复

### 1. 数据库备份

```bash
# 备份
docker exec mysql mysqldump -ugch -pYourPassword123! game_claim_helper > backup_$(date +%Y%m%d).sql

# 恢复
docker exec -i mysql mysql -ugch -pYourPassword123! game_claim_helper < backup_20240101.sql
```

### 2. Redis 备份

```bash
# 触发 RDB 快照
docker exec redis redis-cli -a YourRedisPassword BGSAVE

# 复制备份文件
docker cp redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

### 3. 自动备份脚本

创建备份脚本：
```bash
vim /opt/scripts/backup.sh
```

内容：
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份 MySQL
docker exec mysql mysqldump -ugch -pYourPassword123! game_claim_helper > $BACKUP_DIR/mysql_$DATE.sql

# 备份 Redis
docker exec redis redis-cli -a YourRedisPassword BGSAVE
sleep 5
docker cp redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# 删除 7 天前的备份
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

添加到 crontab：
```bash
crontab -e
# 每天凌晨 2 点备份
0 2 * * * /opt/scripts/backup.sh >> /opt/logs/backup.log 2>&1
```

## 更新与升级

### 1. Docker 部署更新

```bash
# 拉取最新代码
git pull origin main

# 重新构建镜像
docker build -t game_claim_helper:latest .

# 停止旧容器
docker stop game_claim_helper
docker rm game_claim_helper

# 启动新容器
docker run -d \
  --name game_claim_helper \
  --network game_claim_network \
  --env-file .env \
  -p 8000:8000 \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  game_claim_helper:latest
```

### 2. 手动部署更新

```bash
# 拉取最新代码
git pull origin main

# 激活虚拟环境
source venv/bin/activate

# 更新依赖
pip install -r requirements.txt

# 重启服务
sudo systemctl restart game_claim_helper
```

## 安全建议

1. **修改默认密码**: 修改 MySQL、Redis 的默认密码
2. **配置防火墙**: 只开放必要端口（80, 443, 22）
3. **定期更新**: 定期更新系统和依赖包
4. **启用 HTTPS**: 使用 Let's Encrypt 免费 SSL 证书
5. **备份数据**: 定期备份数据库和配置文件
6. **监控日志**: 定期检查应用和系统日志

## 性能优化

1. **数据库优化**:
   - 添加适当的索引
   - 配置连接池
   - 定期清理旧数据

2. **Redis 优化**:
   - 配置内存限制
   - 启用持久化
   - 使用合适的数据结构

3. **应用优化**:
   - 使用 Gunicorn 多进程
   - 配置合适的 worker 数量
   - 启用日志异步写入

## 联系支持

如遇到问题，请：
1. 查看应用日志
2. 查阅本文档的故障排查章节
3. 提交 GitHub Issue
4. 联系项目维护者
