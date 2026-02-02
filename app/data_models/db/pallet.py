"""
托盘（Pallet）数据模型
存储托盘信息，用于港后运输追踪
"""
from sqlalchemy import Boolean, Column, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base


class Pallet(Base):
    """
    托盘表
    对应 Django 模型中的 warehouse_pallet 表
    """
    __tablename__ = "warehouse_pallet"

    id = Column(Integer, primary_key=True, index=True)
    container_number_id = Column(
        Integer, ForeignKey("warehouse_container.id"), nullable=True
    )
    master_shipment_batch_number_id = Column(
        Integer, ForeignKey("warehouse_shipment.id"), nullable=True
    )

    destination = Column(String(255), nullable=True)
    address = Column(String(2000), nullable=True)
    zipcode = Column(String(20), nullable=True)
    delivery_method = Column(String(255), nullable=True)
    delivery_type = Column(String(255), nullable=True)
    pallet_id = Column(String(255), nullable=True)
    PO_ID = Column(String(20), nullable=True)
    shipping_mark = Column(String(4000), nullable=True)
    fba_id = Column(String(4000), nullable=True)
    ref_id = Column(String(4000), nullable=True)
    pcs = Column(Integer, nullable=True)
    sequence_number = Column(String(2000), nullable=True)
    length = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    cbm = Column(Float, nullable=True)
    weight_lbs = Column(Float, nullable=True)
    abnormal_palletization = Column(Boolean, default=False, nullable=True)
    po_expired = Column(Boolean, default=False, nullable=True)
    note = Column(String(2000), nullable=True)
    priority = Column(String(20), nullable=True)
    location = Column(String(100), nullable=True)
    contact_name = Column(String(255), nullable=True)

    # 关联关系
    container = relationship("Container", backref="pallets")
    shipment = relationship(
        "Shipment",
        foreign_keys=[master_shipment_batch_number_id],
        backref="pallets_master"
    )

    __table_args__ = (Index("ix_pallet_PO_ID", "PO_ID"),)
