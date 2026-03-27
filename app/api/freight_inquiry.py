"""
运费询价接口模块

【功能说明】
1. 查询最新报价表
2. 支持三个仓库的报价查询 (NJ, SAV, LA)
3. 同时计算组合柜和转运方式价格

【业务规则】
1. 查询最新报价表：effective_date <= 当前日期，is_user_exclusive=False，quote_type='receivable'
2. 按仓库查询费用详情：
   - NJ: NJ_LOCAL, NJ_PUBLIC, NJ_COMBINA
   - SAV: SAV_PUBLIC, SAV_COMBINA
   - LA: LA_PUBLIC, LA_COMBINA
3. 组合柜计算需要体积和柜型信息
4. 转运方式按区域和目的地查找费率
"""
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.data_models.db import QuotationMaster, FeeDetail
from app.data_models.freight_inquiry import (
    FreightInquiryRequest,
    FreightInquiryResponse,
    QuoteResult,
)
from app.services.db_session import db_session
from app.services.user_auth import get_current_user, CurrentUser

router = APIRouter()


def get_latest_quotation(db: Session) -> Optional[QuotationMaster]:
    """
    获取最新的报价表
    
    Args:
        db: 数据库会话
    
    Returns:
        最新的报价表，如果没有则返回None
    """
    today = date.today()
    return (
        db.query(QuotationMaster)
        .filter(
            and_(
                QuotationMaster.effective_date <= today,
                QuotationMaster.is_user_exclusive == False,
                QuotationMaster.quote_type == "receivable",
            )
        )
        .order_by(desc(QuotationMaster.effective_date))
        .first()
    )


def calculate_combina_price(
    warehouse: str,
    fee_detail: FeeDetail,
    pallets: int,
    cbm: Optional[float],
    container_cbm: Optional[float],
    container_type: Optional[str],
    quotation_name: str,
) -> QuoteResult:
    """
    计算组合柜价格
    
    Args:
        warehouse: 仓库代码
        fee_detail: 费用详情
        pallets: 板数
        cbm: 货物体积
        container_cbm: 整柜体积
        container_type: 柜型
        quotation_name: 报价表名称
    
    Returns:
        报价结果
    """
    if not cbm or not container_cbm or not container_type:
        return QuoteResult(
            warehouse=warehouse,
            quote_type="COMBINA",
            rate_found=False,
            message="缺少体积或柜型信息，无法计算组合柜价格",
        )

    rules = fee_detail.details or {}
    container_type_temp = 0 if "40" in container_type else 1

    try:
        rate_table = rules.get(str(container_type_temp), {})
        rate = None
        
        for min_cbm, rate_value in sorted(rate_table.items(), key=lambda x: float(x[0])):
            if cbm >= float(min_cbm):
                rate = float(rate_value)
        
        if rate is None:
            return QuoteResult(
                warehouse=warehouse,
                quote_type="COMBINA",
                rate_found=False,
                message="未找到匹配的组合柜费率",
            )

        amount = rate * pallets
        return QuoteResult(
            warehouse=warehouse,
            quote_type="COMBINA",
            rate_found=True,
            rate=rate,
            amount=amount,
            message=f"组合柜报价 ({container_type})",
        )
    except Exception as e:
        return QuoteResult(
            warehouse=warehouse,
            quote_type="COMBINA",
            rate_found=False,
            message=f"组合柜计算失败: {str(e)}",
        )


def calculate_public_price(
    warehouse: str,
    fee_detail: FeeDetail,
    pallets: int,
    quotation_name: str,
) -> List[QuoteResult]:
    """
    计算转运方式价格 (PUBLIC)
    
    Args:
        warehouse: 仓库代码
        fee_detail: 费用详情
        pallets: 板数
        quotation_name: 报价表名称
    
    Returns:
        报价结果列表
    """
    results = []
    rules = fee_detail.details or {}

    details = (
        {"LA_AMAZON": rules} if "LA" in warehouse and "LA_AMAZON" not in rules else rules
    )

    for category, zones in details.items():
        if "AMAZON" in category:
            delivery_type = "PUBLIC_AMAZON"
        elif "WALMART" in category:
            delivery_type = "PUBLIC_WALMART"
        else:
            continue

        if not zones:
            continue

        try:
            first_zone = list(zones.keys())[0]
            rate = float(first_zone) if first_zone else 0.0

            amount = rate * pallets
            results.append(
                QuoteResult(
                    warehouse=warehouse,
                    quote_type=delivery_type,
                    rate_found=True,
                    rate=rate,
                    amount=amount,
                    message=f"{delivery_type.replace('_', ' ')} 报价",
                )
            )
        except Exception as e:
            results.append(
                QuoteResult(
                    warehouse=warehouse,
                    quote_type=delivery_type,
                    rate_found=False,
                    message=f"{delivery_type} 计算失败: {str(e)}",
                )
            )

    return results


@router.post("/freight_inquiry", response_model=FreightInquiryResponse, name="freight_inquiry")
async def get_freight_inquiry(
    request: FreightInquiryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> FreightInquiryResponse:
    """
    运费询价接口
    
    【功能说明】
    1. 查询最新报价表
    2. 查询三个仓库的报价 (NJ, SAV, LA)
    3. 同时计算组合柜和转运方式价格
    
    Args:
        request: 询价请求，包含 warehouse, pallets, cbm, container_cbm, container_type
        current_user: 当前登录用户
        db: 数据库会话
    
    Returns:
        FreightInquiryResponse: 询价响应，包含报价结果列表
    
    示例请求:
        POST /freight_inquiry
        Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
        Content-Type: application/json
        {
            "warehouse": "NJ",
            "pallets": 5,
            "cbm": 15.0,
            "container_cbm": 68.0,
            "container_type": "40HQ"
        }
    
    示例响应:
        {
            "success": true,
            "quotes": [
                {
                    "warehouse": "NJ",
                    "quote_type": "COMBINA",
                    "rate_found": true,
                    "rate": 100.0,
                    "amount": 500.0,
                    "message": "组合柜报价 (40HQ)"
                },
                {
                    "warehouse": "NJ",
                    "quote_type": "PUBLIC_AMAZON",
                    "rate_found": true,
                    "rate": 120.0,
                    "amount": 600.0,
                    "message": "PUBLIC AMAZON 报价"
                }
            ],
            "quotation_name": "2026-01-01 报价表",
            "message": null
        }
    """
    try:
        quotation = get_latest_quotation(db)
        
        if not quotation:
            return FreightInquiryResponse(
                success=False,
                quotes=[],
                quotation_name=None,
                message="未找到有效的报价表",
            )

        warehouses = [request.warehouse] if request.warehouse else ["NJ", "SAV", "LA"]
        quotes: List[QuoteResult] = []

        for warehouse in warehouses:
            fee_types = {
                "NJ": ["NJ_COMBINA", "NJ_PUBLIC"],
                "SAV": ["SAV_COMBINA", "SAV_PUBLIC"],
                "LA": ["LA_COMBINA", "LA_PUBLIC"],
            }.get(warehouse, [])

            if not fee_types:
                continue

            fees_list = (
                db.query(FeeDetail)
                .filter(
                    and_(
                        FeeDetail.quotation_id == quotation.id,
                        FeeDetail.fee_type.in_(fee_types),
                    )
                )
                .all()
            )
            fees_dict = {fee.fee_type: fee for fee in fees_list}

            combina_key = f"{warehouse}_COMBINA"
            if combina_key in fees_dict:
                combina_result = calculate_combina_price(
                    warehouse=warehouse,
                    fee_detail=fees_dict[combina_key],
                    pallets=request.pallets,
                    cbm=request.cbm,
                    container_cbm=request.container_cbm,
                    container_type=request.container_type,
                    quotation_name=quotation.filename or "",
                )
                quotes.append(combina_result)

            public_key = f"{warehouse}_PUBLIC"
            if public_key in fees_dict:
                public_results = calculate_public_price(
                    warehouse=warehouse,
                    fee_detail=fees_dict[public_key],
                    pallets=request.pallets,
                    quotation_name=quotation.filename or "",
                )
                quotes.extend(public_results)

        return FreightInquiryResponse(
            success=True,
            quotes=quotes,
            quotation_name=quotation.filename,
            message=None,
        )

    except Exception as e:
        print(f"Freight inquiry error: {str(e)}")
        return FreightInquiryResponse(
            success=False,
            quotes=[],
            quotation_name=None,
            message=f"询价失败: {str(e)}",
        )
