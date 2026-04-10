# 游戏数据存储重构：MySQL → Redis

## 📊 重构原因

**问题**：免费游戏数据每周刷新，不需要持久化存储，MySQL存储过于重量级

**解决方案**：使用Redis缓存游戏数据，提升性能并简化架构

## ✅ 已完成的修改

### 1. **scraper_service.py** - 数据存储改为Redis

**修改内容**：
- ❌ 移除MySQL存储逻辑
- ✅ 添加Redis存储逻辑
- ✅ 日期序列化为ISO格式字符串

**关键代码**：
```python
# 存储到Redis
redis_client.set_current_week_games(games["current"])
redis_client.set_next_week_games(games["upcoming"])
```

### 2. **message_handler.py** - 数据读取改为Redis

**修改内容**：
- ❌ 移除 `GameRepository` 依赖
- ❌ 移除 `FreeGame` 模型依赖
- ✅ 添加 `_get_active_games()` - 从Redis获取当前免费游戏
- ✅ 添加 `_get_upcoming_games()` - 从Redis获取即将免费游戏
- ✅ 修改 `_do_claim()` - 参数改为字典类型
- ✅ 修改 `_get_current_games_message()` - 使用Redis数据
- ✅ 修改 `_get_upcoming_games_message()` - 使用Redis数据

**新增方法**：
```python
def _get_active_games(self) -> List[Dict[str, Any]]:
    """从Redis获取当前免费游戏（正在免费期内）"""
    games = redis_client.get_current_week_games()
    # 过滤出正在免费的游戏
    ...
```

### 3. **Redis数据结构**

**当前免费游戏**：
```
Key: free_games:current_week
Type: List
Value: [game1_json, game2_json, ...]
```

**下周预告游戏**：
```
Key: free_games:next_week
Type: List
Value: [game1_json, game2_json, ...]
```

**游戏数据格式**：
```json
{
  "name": "游戏名称",
  "start_time": "2026-04-02T00:00:00+00:00",
  "end_time": "2026-04-16T15:00:00+00:00",
  "image_url": "https://...",
  "link": "https://store.epicgames.com/...",
  "offer_id": "9f67865fcf0749a58f4d35827473266f",
  "namespace": "7de6896ed120435fba9433d2732dadb4",
  "note": "game-slug"
}
```

## 📋 数据库变更

### MySQL表（保留）

- ✅ `user` - 用户表（需要持久化）
- ✅ `push_log` - 推送日志表（需要持久化）
- ⚠️ `free_game` - 游戏表（保留，但不再作为主数据源）

### Redis键（新增）

- ✅ `free_games:current_week` - 当前免费游戏列表
- ✅ `free_games:next_week` - 下周预告游戏列表
- ✅ `wechat:user_state:{user_id}` - 用户多轮对话状态

## 🚀 部署步骤

### 步骤1：上传代码到服务器

```bash
# 方法A: 使用Git
cd /Users/chen/codeRepository/game_claim_helper
git add .
git commit -m "refactor: 使用Redis存储游戏数据"
git push

# 在服务器上
ssh ubuntu@101.42.17.176
cd /path/to/project
git pull

# 方法B: 直接上传
scp -r app ubuntu@101.42.17.176:/path/to/project/
```

### 步骤2：验证Redis连接

```bash
# 在服务器上测试Redis
redis-cli -h localhost -p 6379 ping
# 应该返回: PONG
```

### 步骤3：刷新游戏数据

```bash
# 方法A: 通过微信
发送消息: "刷新"

# 方法B: 手动执行
python3 -c "from app.services.game.scraper_service import fetch_and_store_games; fetch_and_store_games()"

# 方法C: 调用API
curl http://localhost:8000/api/games/refresh
```

### 步骤4：验证数据

```bash
# 检查Redis中的游戏数据
redis-cli -h localhost -p 6379
> LLEN free_games:current_week
> LRANGE free_games:current_week 0 -1
```

### 步骤5：重启服务

```bash
# 停止旧服务
pkill -f "python.*run.py"

# 启动新服务
nohup python3 run.py > logs/app.log 2>&1 &

# 查看日志
tail -f logs/app.log
```

## 🧪 测试验证

### 测试1：游戏查询

在微信中发送：
```
游戏
```

**预期结果**：返回当前免费游戏的图文消息（2款游戏）

### 测试2：游戏领取

在微信中发送：
```
领取
```

**预期结果**：成功领取游戏或显示失败原因

### 测试3：游戏刷新

在微信中发送：
```
刷新
```

**预期结果**：返回刷新成功消息，显示游戏数量

## 📊 性能对比

### MySQL方案

- ✅ 数据持久化
- ❌ 读写较慢
- ❌ 需要维护表结构
- ❌ 数据冗余（过期游戏）

### Redis方案

- ✅ 读写极快
- ✅ 无需表结构维护
- ✅ 自动过期（可选）
- ✅ 减少数据库压力
- ⚠️ 数据不持久（重启后需要刷新）

## 🔄 数据刷新策略

### 自动刷新（推荐）

**定时任务**（已在 `scheduler.py` 配置）：
```python
# 每小时检查一次
@scheduler.scheduled_job('cron', hour='*', id='refresh_games')
def refresh_games():
    fetch_and_store_games()
```

### 手动刷新

**微信命令**：
```
刷新
```

**API调用**：
```bash
curl http://localhost:8000/api/games/refresh
```

## 🔍 故障排查

### 问题1：Redis连接失败

**错误**：`Connection refused`

**解决**：
```bash
# 检查Redis服务
sudo systemctl status redis

# 启动Redis
sudo systemctl start redis
```

### 问题2：游戏数据为空

**检查**：
```bash
redis-cli
> KEYS free_games:*
```

**解决**：
```bash
# 手动刷新
python3 -c "from app.services.game.scraper_service import fetch_and_store_games; fetch_and_store_games()"
```

### 问题3：游戏查询失败

**日志**：
```bash
tail -f logs/app.log | grep "游戏"
```

## 💡 优化建议

### 建议1：添加Redis过期时间

```python
# 在 scraper_service.py 中修改
redis_client.set_current_week_games(games["current"])
# 添加7天过期时间
redis_client.client.expire("free_games:current_week", 7 * 24 * 3600)
```

### 建议2：添加数据备份

```python
# 刷新前备份旧数据
old_games = redis_client.get_current_week_games()
redis_client.client.set("free_games:current_week:backup", json.dumps(old_games))
```

### 建议3：监控Redis内存

```bash
# 查看Redis内存使用
redis-cli info memory
```

## 📝 配置文件

**.env**（已配置）：
```bash
DATABASE_URL="mysql+pymysql://gch_user:Gch1024!@localhost:3306/game_claim_helper"
REDIS_URL="redis://:onlineRedis1024!@localhost:6379/0"
```

## ✅ 重构完成

**变更总结**：
- ✅ 游戏数据存储：MySQL → Redis
- ✅ 数据读取：ORM查询 → Redis读取
- ✅ 数据刷新：更新数据库 → 更新Redis
- ✅ 性能提升：数据库查询 → 内存读取

**保留功能**：
- ✅ 用户数据仍存储在MySQL
- ✅ 推送日志仍存储在MySQL
- ✅ 所有业务逻辑保持不变

**下一步**：
1. 部署代码到服务器
2. 测试游戏查询功能
3. 测试游戏领取功能
4. 监控Redis性能

---

**重构时间**：2026-04-10 22:48:00  
**影响范围**：游戏数据存储层  
**测试状态**：待部署测试  
