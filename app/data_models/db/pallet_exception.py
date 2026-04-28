"""
Pallet异常数据模型
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.data_models.db.base import Base


class PalletException(Base):
    """
    Pallet异常表
    """
    __tablename__ = "warehouse_palletexception"

    id = Column(Integer, primary_key=True, index=True)
    pallet_id = Column(Integer, ForeignKey("warehouse_pallet.id"), nullable=False)
    exception_type = Column(String(50), nullable=False)
    exception_reason = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联关系
    pallet = relationship("Pallet", backref="exceptions")

    __table_args__ = (
        Index("idx_palletexception_pallet", "pallet_id"),
        Index("idx_palletexception_type", "exception_type"),
    )
