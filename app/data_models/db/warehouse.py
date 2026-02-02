"""
仓库（Warehouse）数据模型
存储仓库信息
"""
from sqlalchemy import Column, Integer, String

from app.data_models.db.base import Base


class Warehouse(Base):
    """
    仓库表
    对应 Django 模型中的 warehouse_zemwarehouse 表
    """
    __tablename__ = "warehouse_zemwarehouse"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    address = Column(String(500), nullable=True)
