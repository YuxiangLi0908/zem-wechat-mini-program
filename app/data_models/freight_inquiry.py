"""
运费询价数据模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class QuoteResult(BaseModel):
    """
    单个报价结果
    """
    warehouse: str = Field(..., description="仓库代码 (NJ/SAV/LA)")
    quote_type: str = Field(..., description="报价类型 (COMBINA/PUBLIC_AMAZON/PUBLIC_WALMART)")
    rate_found: bool = Field(..., description="是否找到报价")
    rate: Optional[float] = Field(None, description="单价")
    amount: Optional[float] = Field(None, description="总价 (单价 × 板数)")
    message: Optional[str] = Field(None, description="提示信息")


class FreightInquiryRequest(BaseModel):
    """
    运费询价请求
    """
    destination: Optional[str] = Field(None, description="仓点 (ACY2/MCO1)")
    pallets: int = Field(..., ge=1, description="板数")
    cbm: float = Field(..., description="体积(CBM)")
    container_cbm: Optional[float] = Field(None, description="整柜体积(CBM)，组合柜计算需要")
    container_type: Optional[str] = Field(None, description="柜型 (40HQ/GP/45HQ/GP)，组合柜计算需要")


class FreightInquiryResponse(BaseModel):
    """
    运费询价响应
    """
    success: bool = Field(True, description="是否成功")
    quotes: List[QuoteResult] = Field(default_factory=list, description="报价结果列表")
    quotation_name: Optional[str] = Field(None, description="使用的报价表名称")
    message: Optional[str] = Field(None, description="提示信息")
