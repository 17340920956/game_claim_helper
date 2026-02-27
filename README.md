# Game Claim Helper

一个自动化的 Epic Games 免费游戏领取助手，支持通过微信公众号（服务号）和 QQ 机器人推送通知，并允许用户通过回复消息进行确认或标记领取。

## 🏗 项目结构

本项目采用模块化分层架构，各模块职责清晰，便于维护和扩展。

```text
game_claim_helper/
├── config/                 # [配置中心]
│   ├── app.py              # 基础应用配置
│   ├── database.py         # 数据库与Redis连接配置
│   ├── epic.py             # Epic爬虫相关配置
│   ├── qq.py               # QQ机器人配置
│   └── wechat.py           # 微信公众号配置
│
├── core/                   # [核心组件]
│   └── scheduler.py        # APScheduler定时任务调度器
│
├── db/                     # [数据持久层]
│   ├── connection.py       # SQLAlchemy数据库连接
│   ├── models.py           # ORM数据模型 (User, PushLog)
│   ├── redis.py            # Redis客户端封装
│   └── schemas.py          # Pydantic数据校验模型
│
├── services/               # [业务逻辑层]
│   ├── game/               # 游戏相关服务
│   │   └── scraper.py      # Epic免费游戏爬虫
│   └── notification/       # 消息推送服务
│       ├── base.py         # 推送器抽象基类
│       ├── service.py      # 统一推送服务入口
│       ├── qq/             # QQ推送实现
│       └── wechat/         # 微信公众号推送实现
│
├── routers/                # [接口路由层]
│   └── wechat.py           # 微信回调接口
│
├── main.py                 # [应用入口] FastAPI启动文件
├── docker-compose.yml      # Docker编排配置
└── requirements.txt        # 依赖清单
```

## ✨ 核心功能

1.  **自动爬取**: 每周四晚定时抓取 Epic Store 最新免费游戏数据。
2.  **多渠道推送**: 支持 **微信公众号** 和 **QQ 机器人** 推送。
3.  **交互确认**: 用户可回复 "确认" 或 "领取" 来更新状态。
4.  **智能调度**: 自动处理数据更新、消息推送和失败重试。
5.  **去重机制**: 基于 Redis 的精准去重，避免重复打扰。

## 🚀 快速开始 (Docker)

1.  **克隆代码**:
    ```bash
    git clone https://github.com/17340920956/game_claim_helper.git
    cd game_claim_helper
    ```

2.  **配置环境**:
    复制 `.env.example` 为 `.env` 并填入您的配置信息。
    ```bash
    cp .env.example .env
    ```

3.  **启动服务**:
    ```bash
    docker-compose up -d
    ```

4.  **访问服务**:
    API 文档地址: `http://localhost:8000/docs`
