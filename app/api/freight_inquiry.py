"""
运费询价接口模块

【功能说明】
1. 查询最新报价表
2. 支持三个仓库的报价查询 (NJ, SAV, LA)
3. 同时计算组合柜和转运方式价格

【业务规则】
1. 查询最新报价表：
   - 优先查找 is_user_exclusive=True 且 exclusive_user=当前用户的报价
   - 如果找不到，再找 is_user_exclusive=False 的通用报价
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

from app.data_models.db.quotation import QuotationMaster, FeeDetail
from app.data_models.freight_inquiry import (
    FreightInquiryRequest,
    FreightInquiryResponse,
    QuoteResult,
)
from app.services.db_session import db_session
from app.services.user_auth import get_current_user, CurrentUser

router = APIRouter()


def get_latest_quotation(db: Session, current_user: CurrentUser) -> Optional[QuotationMaster]:
    """
    获取最新的报价表
    
    【查询优先级】
    1. 优先查找用户专属报价：is_user_exclusive=True, exclusive_user=当前用户名
    2. 如果找不到，再找通用报价：is_user_exclusive=False
    
    Args:
        db: 数据库会话
        current_user: 当前登录用户
    
    Returns:
        最新的报价表，如果没有则返回None
    """
    today = date.today()
    
    quotation = (
        db.query(QuotationMaster)
        .filter(
            and_(
                QuotationMaster.effective_date <= today,
                QuotationMaster.is_user_exclusive == True,
                QuotationMaster.exclusive_user == current_user.zem_name,
                QuotationMaster.quote_type == "receivable",
            )
        )
        .order_by(desc(QuotationMaster.effective_date))
        .first()
    )
    
    if not quotation:
        quotation = (
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
    
    return quotation

def _process_destination(destination_origin):
    """处理目的地字符串"""

    def clean_all_spaces(s):
        if not s:
            return ""
        import re
        cleaned = re.sub(r'[\xa0\u3000\s]+', '', str(s))
        return cleaned
    
    destination_origin = str(destination_origin)

    if "改" in destination_origin or "送" in destination_origin:
        first_change_pos = min(
            (destination_origin.find(char) for char in ["改", "送"] 
            if destination_origin.find(char) != -1),
            default=-1
        )
        
        if first_change_pos != -1:
            first_part = destination_origin[:first_change_pos + 1]
            second_part = destination_origin[first_change_pos + 1:]
            
            if "-" in first_part:
                if first_part.upper().startswith("UPS-"):
                    first_result = first_part
                else:
                    first_result = first_part.split("-", 1)[1]
            else:
                first_result = first_part
            
            if "-" in second_part:
                if second_part.upper().startswith("UPS-"):
                    second_result = second_part
                else:
                    second_result = second_part.split("-", 1)[1]
            else:
                second_result = second_part
            
            return clean_all_spaces(first_result), clean_all_spaces(second_result)
        else:
            raise ValueError(first_change_pos)
    
    if "-" in destination_origin:
        if destination_origin.upper().startswith("UPS-"):
            second_result = destination_origin
        else:
            second_result = destination_origin.split("-", 1)[1]
    else:
        second_result = destination_origin
    
    return None, clean_all_spaces(second_result)

def calculate_combina_price(
    warehouse: str,
    fee_detail: FeeDetail,
    pallets: int,
    cbm: Optional[float],
    destination: Optional[str],
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
    if not cbm or not container_type:
        return QuoteResult(
            warehouse=warehouse,
            quote_type="COMBINA",
            rate_found=False,
            message="缺少体积或柜型信息，无法计算组合柜价格",
        )

    rules = fee_detail.details or {}
    container_type_temp = 0 if "40" in container_type else 1

    destination_origin, destination = _process_destination(destination)

    try:
        is_combina_region = False
        rate = 0
        for region, region_data in rules.items():
            for item in region_data:
                normalized_locations = [loc.strip() for loc in item["location"] if loc]
                if destination in normalized_locations:
                    is_combina_region = True
                    price_group = item["prices"]
                    rate = price_group[container_type_temp]
                    break
            if is_combina_region:
                break
        if destination.upper() == "UPS":
            is_combina_region = False
        if is_combina_region:
            return QuoteResult(
                warehouse=warehouse,
                quote_type="COMBINA",
                rate_found=True,
                rate=rate,
                amount=rate,
                message=f"组合柜报价 ({container_type})",
            )
        else:
            return QuoteResult(
                warehouse=warehouse,
                quote_type="COMBINA",
                rate_found=False,
                message="未找到匹配的组合柜费率",
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
    cbm: float,
    destination: str,
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
    niche_warehouse_str = fee_detail.niche_warehouse or ""
    niche_warehouse_list = [x.strip() for x in niche_warehouse_str.split(",") if x.strip()]
    if destination in niche_warehouse_list:
        is_niche_warehouse = True
    else:
        is_niche_warehouse = False

    delivery_category = None
    rate_found = False
    rate = 0
    for category, zones in details.items():
        for zone, locations in zones.items():
            if destination in locations:
                if "AMAZON" in category:
                    delivery_category = "PUBLIC_AMAZON"
                    rate = zone
                    rate_found = True
                elif "WALMART" in category:
                    delivery_category = "PUBLIC_WALMART"
                    rate = zone
                    rate_found = True
        if rate_found:
            break
    if rate_found:
        cacl_pallet = _calculate_total_pallet(cbm, is_niche_warehouse)
        final_pallet = max(cacl_pallet, pallets)
        amount = rate * final_pallet
        results.append(
            QuoteResult(
                warehouse=warehouse,
                quote_type=delivery_category,
                rate_found=True,
                rate=rate,
                amount=amount,
                message=f"{delivery_category.replace('_', ' ')} 报价",
            )
        )
    else:
        results.append(
            QuoteResult(
                warehouse=warehouse,
                quote_type="PUBLIC",
                rate_found=False,
                message="未找到匹配的转运费率",
            )
        )

    return results

def _calculate_total_pallet(cbm: float, is_niche_warehouse: bool) -> float:
    """板数计算公式"""
    raw_p = float(cbm) / 2
    integer_part = int(raw_p)
    decimal_part = raw_p - integer_part

    if decimal_part > 0:
        if is_niche_warehouse:
            additional = 1 if decimal_part > 0.5 else 0.5
        else:
            additional = 1 if decimal_part > 0.5 else 0
        total_pallet = integer_part + additional
    elif decimal_part == 0:
        total_pallet = integer_part
    else:
        ValueError("板数计算错误")
    return total_pallet


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
        request: 询价请求，包含 destination, pallets, cbm, container_cbm, container_type
        current_user: 当前登录用户
        db: 数据库会话
    
    Returns:
        FreightInquiryResponse: 询价响应，包含报价结果列表
    
    示例请求:
        POST /freight_inquiry
        Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
        Content-Type: application/json
        {
            "destination": "ACY2",
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
        quotation = get_latest_quotation(db, current_user)
        
        if not quotation:
            return FreightInquiryResponse(
                success=False,
                quotes=[],
                quotation_name=None,
                message="未找到有效的报价表",
            )

        warehouses = ["NJ", "SAV", "LA"]
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
                        FeeDetail.quotation_id_id == quotation.id,
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
                    destination=request.destination,
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
                    cbm=request.cbm,
                    destination=request.destination,
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
