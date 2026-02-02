"""
提柜（Retrieval）数据模型
存储提柜相关信息，包括预约提柜、实际提柜时间等
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String

from app.data_models.db.base import Base


class Retrieval(Base):
    """
    提柜表
    对应 Django 模型中的 warehouse_retrieval 表
    """
    __tablename__ = "warehouse_retrieval"

    id = Column(Integer, primary_key=True, index=True)
    retrieval_id = Column(String(255), nullable=True)
    shipping_order_number = Column(String(255), nullable=True)
    master_bill_of_lading = Column(String(255), nullable=True)
    retrive_by_zem = Column(Boolean, nullable=True)
    retrieval_carrier = Column(String(255), nullable=True)
    origin_port = Column(String(255), nullable=True)
    destination_port = Column(String(255), nullable=True)
    shipping_line = Column(String(255), nullable=True)
    retrieval_destination_precise = Column(String(500), nullable=True)
    assigned_by_appt = Column(Boolean, nullable=True)
    retrieval_destination_area = Column(String(255), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    target_retrieval_timestamp = Column(DateTime, nullable=True)
    target_retrieval_timestamp_lower = Column(DateTime, nullable=True)
    actual_retrieval_timestamp = Column(DateTime, nullable=True)
    note = Column(String(2000), nullable=True)
    arrive_at_destination = Column(Boolean, nullable=True)
    arrive_at = Column(DateTime, nullable=True)
    empty_returned = Column(Boolean, nullable=True)
    empty_returned_at = Column(DateTime, nullable=True)
    temp_t49_lfd = Column(Date, nullable=True)
    temp_t49_available_for_pickup = Column(Boolean, nullable=True)
    temp_t49_pod_arrive_at = Column(DateTime, nullable=True)
    temp_t49_pod_discharge_at = Column(DateTime, nullable=True)
    temp_t49_hold_status = Column(Boolean, nullable=True)
