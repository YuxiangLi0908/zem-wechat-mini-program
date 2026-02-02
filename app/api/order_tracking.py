"""
柜号查询接口模块

【关键业务规则】
1. 客户登录：查询柜号时需验证该柜子是否归属此客户
   - 通过订单的 customer_name_id 关联判断归属
   - 非归属柜子返回 has_permission=False，不展示详情
   
2. 员工登录：查询柜号时无需验证归属
   - 直接返回所有柜子详情

【接口说明】
- 需要 Bearer Token 认证
- 返回完整的港前+港后追踪信息
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data_models.order_tracking import OrderResponse, OrderTrackingRequest
from app.services.db_session import db_session
from app.services.order_history import OrderTracking
from app.services.user_auth import get_current_user, CurrentUser

router = APIRouter()


@router.post("/order_tracking", response_model=OrderResponse, name="order_tracking")
async def get_order_full_history(
    request: OrderTrackingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> OrderResponse:
    """
    柜号查询接口
    
    【权限验证逻辑】
    1. 从 Bearer Token 获取当前用户信息
    2. 根据用户类型进行权限验证：
       - 客户用户：验证柜号归属，仅能查看自己的柜子
       - 员工用户：无需验证，可查看所有柜子
    
    Args:
        request: 查询请求，包含 container_number（柜号）
        current_user: 当前登录用户（从 Token 解析）
        db: 数据库会话
    
    Returns:
        OrderResponse: 完整的订单追踪响应，包含：
            - preport_timenode: 港前轨迹
            - postport_timenode: 港后轨迹
            - has_permission: 是否有权限查看
            - message: 附加消息（无权限或未找到时的提示）
    
    示例请求:
        POST /order_tracking
        Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
        Content-Type: application/json
        {
            "container_number": "ABCD1234567"
        }
    
    示例响应（有权限）:
        {
            "preport_timenode": {
                "order_id": "ORD-001",
                "created_at": "2026-01-15T10:00:00",
                "container": {"container_number": "ABCD1234567", ...},
                "history": [
                    {"status": "ORDER_CREATED", "description": "创建订单", ...},
                    {"status": "ARRIVED_AT_PORT", "description": "到达港口", ...}
                ],
                ...
            },
            "postport_timenode": {
                "shipment": [...]
            },
            "has_permission": true,
            "message": null
        }
    
    示例响应（客户无权限）:
        {
            "preport_timenode": null,
            "postport_timenode": null,
            "has_permission": false,
            "message": "您没有权限查看柜号 ABCD1234567 的详情，该柜子归属于其他客户"
        }
    """
    # 清理柜号（去除前后空格）
    container_number = request.container_number.strip()
    
    # 创建订单追踪服务实例
    order_tracking = OrderTracking(
        user=current_user,
        container_number=container_number,
        db_session=db,
    )
    
    # 构建并返回完整的订单追踪历史
    return order_tracking.build_order_full_history()
