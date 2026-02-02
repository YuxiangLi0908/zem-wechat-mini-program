"""
卸货（Offload）数据模型
存储卸货/拆柜相关信息
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.data_models.db.base import Base


class Offload(Base):
    """
    卸货表
    对应 Django 模型中的 warehouse_offload 表
    """
    __tablename__ = "warehouse_offload"

    id = Column(Integer, primary_key=True, index=True)
    offload_id = Column(String(255), nullable=True)
    offload_required = Column(Boolean, nullable=True)
    offload_at = Column(DateTime, nullable=True)
    total_pallet = Column(Integer, nullable=True)
