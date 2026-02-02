"""
车队（Fleet）数据模型
存储车队信息
"""
from sqlalchemy import Column, Integer, String

from app.data_models.db.base import Base


class Fleet(Base):
    """
    车队表
    对应 Django 模型中的 warehouse_fleet 表
    """
    __tablename__ = "warehouse_fleet"

    id = Column(Integer, primary_key=True, index=True)
    fleet_number = Column(String(255), nullable=True)
    carrier = Column(String(255), nullable=True)
