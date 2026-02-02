"""
车队（Fleet）数据模型
存储车队信息
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from app.data_models.db.base import Base


class Fleet(Base):
    """
    车队表
    对应 Django 模型中的 warehouse_fleet 表
    """
    __tablename__ = "warehouse_fleet"

    id = Column(Integer, primary_key=True, index=True)
    fleet_number = Column(String(255), nullable=True)
    fleet_zem_serial = Column(String(255), nullable=True)
    amf_id = Column(String(255), nullable=True)
    fleet_type = Column(String(255), nullable=True)
    origin = Column(String(255), nullable=True)
    carrier = Column(String(100), nullable=True)
    third_party_address = Column(String(500), nullable=True)
    license_plate = Column(String(100), nullable=True)
    driver_phone = Column(String(100), nullable=True)
    driver_name = Column(String(100), nullable=True)
    trailer_number = Column(String(100), nullable=True)
    
    # 仓库处理状态（匹配Django的choices）
    warehouse_process_status = Column(
        String(20), 
        nullable=True, 
        default='waiting'  # 匹配Django的default
    )
    shipped_cert_link = Column(String(2000), nullable=True)
    motor_carrier_number = Column(String(100), nullable=True)
    dot_number = Column(String(100), nullable=True)
    appointment_datetime = Column(DateTime, nullable=True)
    appointment_datetime_tz = Column(String(20), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    departured_at = Column(DateTime, nullable=True)
    arrived_at = Column(DateTime, nullable=True)
    pickup_number = Column(String(500), nullable=True)
    fleet_cost = Column(Float, nullable=True)
    total_weight = Column(Float, nullable=True)
    total_cbm = Column(Float, nullable=True)
    total_pallet = Column(Float, nullable=True)
    total_pcs = Column(Float, nullable=True)
    note = Column(String(1000), nullable=True)
    shipped_weight = Column(Float, nullable=True, default=0.0)
    shipped_cbm = Column(Float, nullable=True, default=0.0)
    shipped_pallet = Column(Float, nullable=True, default=0.0)
    shipped_pcs = Column(Float, nullable=True, default=0.0)
    cost_price = Column(Float, nullable=True, default=0.0)
    multipule_destination = Column(Boolean, nullable=True, default=False)
    pod_link = Column(String(2000), nullable=True)
    pod_uploaded_at = Column(DateTime, nullable=True)
    is_canceled = Column(Boolean, nullable=True, default=False)
    cancelation_reason = Column(String(2000), nullable=True)
    status = Column(String(20), nullable=True)
    status_description = Column(String(1000), nullable=True)
    pre_load = Column(String(1000), nullable=True)
    abnormal_reason = Column(String(1000), nullable=True)
    is_virtual = Column(Boolean, nullable=True, default=False)
    ltl_shipping_tracking = Column(String(1000), nullable=True)
    fleet_cost_back = Column(Float, nullable=True)

    # 可选：为常用查询字段加索引
    __table_args__ = (
        Index("ix_fleet_fleet_number", "fleet_number"),
        Index("ix_fleet_warehouse_process_status", "warehouse_process_status"),
    )
