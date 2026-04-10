#!/usr/bin/env python3
"""
初始化数据库
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine, Base
from app.models.base import User, PushLog

def init_database():
    """初始化数据库"""
    print("开始初始化数据库...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    print("✅ 数据库初始化成功！")
    
    # 验证表是否创建成功
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n创建的表: {', '.join(tables)}")

if __name__ == "__main__":
    init_database()
