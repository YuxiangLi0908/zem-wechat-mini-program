"""
船舶（Vessel）数据模型
存储船舶航运信息
"""
from sqlalchemy import Column, DateTime, Integer, String

from app.data_models.db.base import Base


class Vessel(Base):
    """
    船舶表
    对应 Django 模型中的 warehouse_vessel 表
    """
    __tablename__ = "warehouse_vessel"

    id = Column(Integer, primary_key=True, index=True)
    vessel_id = Column(String(255), nullable=True)
    master_bill_of_lading = Column(String(255), nullable=True)
    origin_port = Column(String(255), nullable=True)
    destination_port = Column(String(255), nullable=True)
    shipping_line = Column(String(255), nullable=True)
    vessel = Column(String(255), nullable=True)
    voyage = Column(String(255), nullable=True)
    vessel_etd = Column(DateTime, nullable=True)
    vessel_eta = Column(DateTime, nullable=True)
