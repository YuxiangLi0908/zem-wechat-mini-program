"""
订单（Order）数据模型
订单是核心业务实体，关联客户、集装箱、仓库、船舶、提柜、卸货等信息

【权限验证关键】
- 通过 customer_name_id 关联到 Customer 表
- 客户登录时，需验证查询的柜号对应的订单是否属于该客户
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base


class Order(Base):
    """
    订单表
    对应 Django 模型中的 warehouse_order 表
    """
    __tablename__ = "warehouse_order"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(255), nullable=True)
    
    # 【关键外键】customer_name_id 关联客户表，用于权限验证
    customer_name_id = Column(
        Integer, ForeignKey("warehouse_customer.id"), nullable=True
    )
    container_number_id = Column(
        Integer, ForeignKey("warehouse_container.id"), nullable=True
    )
    warehouse_id = Column(
        Integer, ForeignKey("warehouse_zemwarehouse.id"), nullable=True
    )
    vessel_id_id = Column(Integer, ForeignKey("warehouse_vessel.id"), nullable=True)
    retrieval_id_id = Column(
        Integer, ForeignKey("warehouse_retrieval.id"), nullable=True
    )
    offload_id_id = Column(Integer, ForeignKey("warehouse_offload.id"), nullable=True)
    shipment_id_id = Column(Integer, ForeignKey("warehouse_shipment.id"), nullable=True)
    invoice_id_id = Column(Integer, ForeignKey("warehouse_invoice.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    eta = Column(Date, nullable=True)
    order_type = Column(String(255), nullable=True)
    customer_do_link = Column(String(2000), nullable=True)
    do_sent = Column(Boolean, default=False)
    add_to_t49 = Column(Boolean, default=False)
    packing_list_updloaded = Column(Boolean, default=False)
    cancel_notification = Column(Boolean, default=False)
    cancel_time = Column(Date, nullable=True)
    invoice_status = Column(String(255), nullable=True)
    invoice_reject = Column(Boolean, default=False)
    invoice_reject_reason = Column(String(255), nullable=True)

    # 关联关系
    user = relationship("Customer", backref="orders")
    container = relationship("Container", backref="orders")
    warehouse = relationship("Warehouse", backref="orders")
    vessel = relationship("Vessel", backref="orders")
    retrieval = relationship("Retrieval", backref="orders")
    offload = relationship("Offload", backref="orders")

    __table_args__ = (
        Index("ix_order_order_id", "order_id"),
        Index("ix_order_eta", "eta"),
        Index("ix_order_created_at", "created_at"),
    )
