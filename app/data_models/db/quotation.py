"""
报价表（QuotationMaster）和费用详情（FeeDetail）数据模型
"""
from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.data_models.db.base import Base


class QuotationMaster(Base):
    """
    报价表版本管理
    对应 Django 模型中的 warehouse_quotationmaster 表
    """
    __tablename__ = "warehouse_quotationmaster"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(String(200), nullable=True)
    upload_date = Column(Date, nullable=True)
    version = Column(String(2000), nullable=True)
    quote_type = Column(String(20), nullable=True)
    filename = Column(String(2000), nullable=True)
    is_user_exclusive = Column(Boolean, default=False)
    exclusive_user = Column(String(2000), nullable=True)
    effective_date = Column(Date, nullable=True)

    __table_args__ = (
        Index("ix_quotationmaster_effective_date", "effective_date"),
        Index("ix_quotationmaster_quote_type", "quote_type"),
    )


class FeeDetail(Base):
    """
    费用详情表
    对应 Django 模型中的 warehouse_feedetail 表
    """
    __tablename__ = "warehouse_feedetail"

    id = Column(Integer, primary_key=True, index=True)
    fee_detail_id = Column(String(200), nullable=True)
    quotation_id_id = Column(Integer, ForeignKey("warehouse_quotationmaster.id"), nullable=True, name="quotation_id_id")
    fee_type = Column(String(255), nullable=True)
    warehouse = Column(String(20), nullable=True)
    details = Column(JSONB, default=dict)
    niche_warehouse = Column(String(2000), nullable=True)

    quotation = relationship("QuotationMaster", backref="fee_details")

    __table_args__ = (
        Index("ix_feedetail_quotation_id_id", "quotation_id_id"),
        Index("ix_feedetail_fee_type", "fee_type"),
    )
