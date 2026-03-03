import sys
from loguru import logger
import os

# Ensure log directory exists
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Remove default handler
logger.remove()

# Add console handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

# Add file handler with rotation and retention
logger.add(
    os.path.join(log_dir, "app.log"),
    rotation="10 MB",
    retention="10 days",
    level="INFO",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)

# Add error file handler
logger.add(
    os.path.join(log_dir, "error.log"),
    rotation="10 MB",
    retention="10 days",
    level="ERROR",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    backtrace=True,
    diagnose=True,
)

__all__ = ["logger"]
