import multiprocessing

# 绑定的IP和端口
bind = "0.0.0.0:8000"

# 工作进程数 (建议 CPU核心数 * 2 + 1)
workers = multiprocessing.cpu_count() * 2 + 1

# 指定 worker 类型为 uvicorn
worker_class = "uvicorn.workers.UvicornWorker"

# 日志配置
accesslog = "-"  # 输出到标准输出
errorlog = "-"   # 输出到标准错误
loglevel = "info"

# 进程名称
proc_name = "game_claim_helper"

# 超时设置
timeout = 120
keepalive = 5
