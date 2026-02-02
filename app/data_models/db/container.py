"""
集装箱（Container）数据模型
存储集装箱的基本信息
"""
from sqlalchemy import Boolean, Column, Float, Integer, String

from app.data_models.db.base import Base


class Container(Base):
    """
    集装箱表
    对应 Django 模型中的 warehouse_container 表
    """
    __tablename__ = "warehouse_container"

    id = Column(Integer, primary_key=True, index=True)
    # container_number: 柜号，查询的主要字段
    container_number = Column(String(255), nullable=True, index=True)
    container_type = Column(String(255), nullable=True)
    weight_lbs = Column(Float, nullable=True)
    is_special_container = Column(Boolean, nullable=True, default=False)
    note = Column(String(100), nullable=True)
