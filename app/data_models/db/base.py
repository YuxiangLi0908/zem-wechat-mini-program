"""
SQLAlchemy 基础模型声明
所有数据库模型类都需要继承此 Base 类
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
