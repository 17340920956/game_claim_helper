import multiprocessing

# 绑定的IP和端口
bind = "0.0.0.0:8000"

# 工作进程数 (设为 1 以避免 APScheduler 定时任务重复执行)
workers = 1

# 指定 worker 类型为 uvicorn
worker_class = "uvicorn.workers.UvicornWorker"

# 日志配置
accesslog = "-"  # 输出到标准输出
errorlog = "-"   # 输出到标准错误
loglevel = "info"

# 进程名称
proc_name = "game_claim_helper"

# 超时设置
timeout = 300
keepalive = 5

# 优雅关闭超时
graceful_timeout = 300
