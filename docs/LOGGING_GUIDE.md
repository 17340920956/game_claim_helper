# 服务器部署日志查看指南

本文档详细说明了在服务器部署环境下（基于 Docker）如何查看和管理 `Game Claim Helper` 项目的日志。

## 1. 快速查看实时日志 (推荐)

由于项目配置了 Gunicorn 和 Loguru 将日志输出到标准输出流，最直接的方法是使用 Docker 命令查看。

### 查看实时滚动日志
```bash
# 查看最后 100 行并持续跟踪
docker-compose logs -f --tail=100 app
```

### 查看特定服务的日志
如果只想看应用服务的日志（排除数据库和 Redis）：
```bash
docker-compose logs app
```

### 导出日志到文件
如果需要分析历史日志，可以将输出重定向到文件：
```bash
docker-compose logs app > service_logs.txt
```

---

## 2. 查看详细日志文件

项目使用 `loguru` 库在容器内部生成了结构化的日志文件，这些文件通常包含比控制台更详细的信息（如完整的错误堆栈）。

### 日志文件位置
容器内部路径：
- **常规日志**: `/app/logs/app.log` (包含 INFO 及以上级别)
- **错误日志**: `/app/logs/error.log` (包含 ERROR 级别及详细堆栈)

### 方法 A: 进入容器查看
```bash
# 1. 进入容器终端
docker-compose exec app /bin/bash

# 2. 查看日志目录
cd logs
ls -lh

# 3. 实时查看日志文件
tail -f app.log
# 或
tail -f error.log

# 4. 退出容器
exit
```

### 方法 B: 拷贝日志到宿主机
如果不想进入容器，可以直接将日志文件复制出来分析：
```bash
# 语法: docker cp <容器ID或名称>:<容器内路径> <宿主机路径>

# 首先获取容器名称（通常是 game_claim_helper-app-1 或类似）
docker ps 

# 拷贝日志目录到当前目录
docker cp $(docker-compose ps -q app):/app/logs ./exported_logs
```

---

## 3. 配置日志持久化 (强烈建议)

为了避免重启容器导致日志丢失，建议将日志目录挂载到宿主机。

### 修改 `docker-compose.yml`

在 `app` 服务的 `volumes` 部分添加映射：

```yaml
services:
  app:
    # ... 其他配置 ...
    volumes:
      - ./logs:/app/logs  # 添加这一行
```

### 重启服务
修改配置后，需要重建容器使配置生效：
```bash
docker-compose up -d --build app
```

这样，你就可以直接在服务器的 `./logs` 目录下查看 `app.log` 和 `error.log`，无需进入容器。

---

## 4. 日志策略说明

项目的日志配置位于 `core/logger.py`：

| 类型 | 文件名 | 轮转策略 (Rotation) | 保留策略 (Retention) | 说明 |
|------|--------|-------------------|--------------------|------|
| 应用日志 | `app.log` | 10 MB | 10 天 | 记录主要业务流程和信息 |
| 错误日志 | `error.log` | 10 MB | 10 天 | 记录异常、报错和详细堆栈 |

*注：日志文件达到 10MB 后会自动切割，旧日志会被压缩归档，最多保留 10 天的历史记录。*
