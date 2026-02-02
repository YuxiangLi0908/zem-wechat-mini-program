"""
集装箱（Container）数据模型
存储集装箱的基本信息
"""
from sqlalchemy import Boolean, Column, Float, Integer, String, Index

from app.data_models.db.base import Base


class Customer(Base):
    """
    客户表
    对应 Django 模型中的 warehouse_customer 表
    """
    __tablename__ = "warehouse_customer"

    id = Column(Integer, primary_key=True, index=True)
    zem_name = Column(String(200), nullable=False)  # Django CharField默认非空，对应nullable=False
    full_name = Column(String(200), nullable=True)
    accounting_name = Column(String(200), nullable=True)
    zem_code = Column(String(20), nullable=True)  # blank=True对应nullable=True
    email = Column(String(100), nullable=True)
    phone = Column(String(30), nullable=True)
    note = Column(String(500), nullable=True)
    address = Column(String(500), nullable=True)
    username = Column(String(150), unique=True, nullable=True)  # unique=True 匹配Django的unique约束
    password = Column(String(255), nullable=True)
    balance = Column(Float, nullable=True, default=0.0)  # default=0.0 匹配Django的default

    # 可选：为常用查询字段加索引（参考Container表的写法）
    __table_args__ = (
        Index("ix_customer_username", "username"),  # 用户名加索引，提升登录查询速度
        Index("ix_customer_zem_name", "zem_name"),  # 客户名称加索引（可选）
    )