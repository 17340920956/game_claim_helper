# Game Claim Helper

## 项目简介

Game Claim Helper 是一个自动化的 Epic Games 免费游戏领取助手，能够自动爬取 Epic Games Store 的免费游戏信息，并通过微信公众号推送通知给用户，帮助用户及时领取免费游戏。

## 核心功能

- **自动爬取**: 每周四定时抓取 Epic Store 最新免费游戏数据
- **智能推送**: 通过微信公众号模板消息推送游戏通知
- **定时调度**: 基于 APScheduler 实现自动化定时任务
- **去重机制**: 基于 Redis 的精准去重，避免重复推送
- **失败重试**: 自动重试失败的推送任务
- **用户管理**: 支持多用户订阅和推送管理

## 技术栈

- **后端框架**: FastAPI
- **数据库**: MySQL (SQLAlchemy ORM)
- **缓存**: Redis
- **任务调度**: APScheduler
- **爬虫**: requests + BeautifulSoup
- **微信公众号**: 微信公众平台 API

## 项目结构

```
game_claim_helper/
├── app/
│   ├── api/                  # API 接口层
│   │   └── endpoints/        # 各类端点
│   │       ├── game.py       # 游戏相关接口
│   │       ├── notification.py # 通知接口
│   │       ├── user.py       # 用户接口
│   │       └── wechat.py     # 微信回调接口
│   ├── clients/              # 外部客户端
│   │   └── wechat/           # 微信 API 客户端
│   ├── core/                 # 核心配置
│   │   ├── config.py         # 配置管理
│   │   ├── logger.py         # 日志配置
│   │   ├── scheduler.py      # 定时任务调度
│   │   └── security.py       # 安全相关
│   ├── db/                   # 数据库层
│   │   ├── redis.py          # Redis 连接
│   │   └── session.py        # 数据库会话
│   ├── models/               # 数据模型
│   ├── repositories/         # 数据仓库层
│   ├── schemas/              # Pydantic 模型
│   ├── services/             # 业务逻辑层
│   │   ├── game/             # 游戏爬虫服务
│   │   └── notification/     # 通知推送服务
│   └── main.py               # 应用入口
├── docs/                     # 文档目录
├── scripts/                  # 脚本工具
├── .env.example              # 环境变量示例
├── docker-compose.yml        # Docker 编排配置
├── Dockerfile                # Docker 镜像构建
├── nginx.conf                # Nginx 配置
└── requirements.txt          # Python 依赖
```

## 定时任务

系统内置以下定时任务：

| 任务 | 时间 | 说明 |
|------|------|------|
| 爬取本周免费游戏 | 每周四 23:05 | Epic 通常在周四 23:00 更新 |
| 爬取下周预告游戏 | 每周四 23:05 | 获取下周即将免费的游戏 |
| 推送本周游戏通知 | 每周五 09:00 | 向用户推送本周免费游戏 |
| 推送下周预告通知 | 每周五 09:30 | 向用户推送下周预告 |
| 重试失败推送 | 每天 10:00-22:00 整点 | 自动重试失败的推送 |

## 快速开始

### 前置要求

- Python 3.9+
- MySQL 5.7+
- Redis 5.0+
- 微信公众号（服务号）

### 本地运行

1. **克隆项目**
```bash
git clone https://github.com/17340920956/game_claim_helper.git
cd game_claim_helper
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入实际配置
```

4. **启动服务**
```bash
python run.py
```

5. **访问服务**
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 环境变量配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| DATABASE_URL | MySQL 连接字符串 | mysql+pymysql://user:password@host:3306/dbname |
| REDIS_URL | Redis 连接字符串 | redis://:password@host:6379/0 |
| EPIC_FREE_GAMES_URL | Epic 免费游戏页面 URL | https://store.epicgames.com/en-US/free-games |
| WECHAT_OFFICIAL_APPID | 微信公众号 AppID | wx1234567890 |
| WECHAT_OFFICIAL_SECRET | 微信公众号 Secret | your_secret_key |
| WECHAT_OFFICIAL_TOKEN | 微信公众号 Token | your_token |
| WECHAT_OFFICIAL_AES_KEY | 微信公众号 EncodingAESKey | your_aes_key |
| SCHEDULER_TIMEZONE | 调度器时区 | Asia/Shanghai |

## 微信公众号配置

1. 登录微信公众平台，进入「设置与开发」->「基本配置」
2. 配置服务器地址: `http://your-domain.com/wechat/callback`
3. 设置 Token 和 EncodingAESKey
4. 配置模板消息，获取模板 ID

## API 接口

### 健康检查
```
GET /health
```

### 微信回调
```
GET/POST /wechat/callback
```

### 用户管理
```
GET /users/          # 获取用户列表
POST /users/         # 创建用户
GET /users/{id}      # 获取用户详情
```

### 游戏管理
```
GET /games/          # 获取游戏列表
GET /games/active    # 获取当前免费游戏
GET /games/upcoming  # 获取即将免费游戏
```

### 通知管理
```
GET /notifications/logs  # 获取推送日志
POST /notifications/test # 测试推送
```

## 开发指南

### 代码规范

- 使用 Black 格式化代码
- 使用 isort 排序导入
- 遵循 PEP 8 规范

### 日志管理

系统使用统一的日志管理器，日志文件位于 `logs/` 目录：
- `app.log`: 应用日志
- `error.log`: 错误日志

### 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head
```

## 常见问题

### 1. 推送失败
- 检查微信公众号配置是否正确
- 确认 access_token 是否有效
- 查看用户是否关注公众号

### 2. 爬虫失败
- 检查网络连接
- 确认 Epic API 是否可访问
- 查看日志中的错误信息

### 3. 定时任务不执行
- 确认调度器是否启动
- 检查时区配置
- 查看调度器日志

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请提交 Issue 或联系项目维护者。
