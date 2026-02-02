"""
运输（Shipment）数据模型
存储运输批次信息，用于港后运输追踪
"""
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base

from app.data_models.db.fleet import Fleet


class Shipment(Base):
    """
    运输表
    对应 Django 模型中的 warehouse_shipment 表
    """
    __tablename__ = "warehouse_shipment"

    id = Column(Integer, primary_key=True, index=True)
    fleet_number_id = Column(Integer, ForeignKey("warehouse_fleet.id"), nullable=True)

    shipment_batch_number = Column(String(255), nullable=True)
    master_batch_number = Column(String(255), nullable=True)
    batch = Column(Integer, nullable=True, default=0)
    appointment_id = Column(String(255), nullable=True)
    origin = Column(String(255), nullable=True)
    destination = Column(String(255), nullable=True)
    address = Column(String(2000), nullable=True)
    carrier = Column(String(255), nullable=True)
    third_party_address = Column(String(500), nullable=True)
    is_shipment_schduled = Column(Boolean, default=False)
    shipment_schduled_at = Column(DateTime, nullable=True)
    shipment_appointment = Column(DateTime, nullable=True)
    shipment_appointment_tz = Column(String(20), nullable=True)
    shipment_appointment_utc = Column(DateTime, nullable=True)
    is_shipped = Column(Boolean, nullable=True, default=False)
    shipped_at = Column(DateTime, nullable=True)
    shipped_at_utc = Column(DateTime, nullable=True)
    is_full_out = Column(Boolean, nullable=True, default=False)
    is_arrived = Column(Boolean, nullable=True, default=False)
    arrived_at = Column(DateTime, nullable=True)
    arrived_at_utc = Column(DateTime, nullable=True)
    load_type = Column(String(255), nullable=True)
    shipment_account = Column(String(255), nullable=True)
    shipment_type = Column(String(255), nullable=True)
    total_weight = Column(Float, nullable=True, default=0)
    total_cbm = Column(Float, nullable=True, default=0)
    total_pallet = Column(Float, nullable=True, default=0)
    total_pcs = Column(Float, nullable=True, default=0)
    shipped_weight = Column(Float, nullable=True, default=0)
    shipped_cbm = Column(Float, nullable=True, default=0)
    shipped_pallet = Column(Float, nullable=True, default=0)
    shipped_pcs = Column(Float, nullable=True, default=0)
    note = Column(String(1000), nullable=True)
    pod_link = Column(String(2000), nullable=True)
    pod_uploaded_at = Column(DateTime, nullable=True)
    pallet_dumpped = Column(Float, nullable=True, default=0)
    abnormal_palletization = Column(Boolean, nullable=True, default=False)
    po_expired = Column(Boolean, nullable=True, default=False)
    in_use = Column(Boolean, nullable=True, default=True)
    is_canceled = Column(Boolean, nullable=True, default=False)
    cancelation_reason = Column(String(2000), nullable=True)
    priority = Column(String(10), nullable=True)
    status = Column(String(20), nullable=True)
    status_description = Column(String(1000), nullable=True)
    previous_fleets = Column(String(1000), nullable=True)
    ARM_BOL = Column(String(255), nullable=True)
    ARM_PRO = Column(String(255), nullable=True)
    express_number = Column(String(255), nullable=True)

    # 关联关系
    fleet = relationship(
        "Fleet",
        backref="shipment",  # 严格匹配Django的related_name="shipment"
        foreign_keys=[fleet_number_id],
        lazy="select"
    )