"""
订单追踪服务模块

提供柜号查询的核心业务逻辑，包括：
1. 港前轨迹查询（订单创建到拆柜完成）
2. 港后轨迹查询（托盘运输状态）
3. 权限验证（客户只能查看自己的柜子）

【关键业务规则】
1. 客户登录：查询柜号时需验证该柜子是否归属此客户
   - 通过订单关联的 customer_name_id 判断归属
   - 非归属柜子返回 has_permission=False
   
2. 员工登录：查询柜号时无需验证归属，可查看所有柜子
"""
from datetime import datetime
from typing import Optional

import pytz
from fastapi import HTTPException
from sqlalchemy import Numeric, cast, distinct, func
from sqlalchemy.orm import Session, joinedload

from app.data_models.db.container import Container
from app.data_models.db.order import Order
from app.data_models.db.pallet import Pallet
from app.data_models.db.shipment import Shipment
from app.data_models.db.pallet_exception import PalletException
from app.data_models.order_tracking import (
    OrderPostportResponse,
    OrderPreportResponse,
    OrderResponse,
    PalletShipmentSummary,
)
from app.services.user_auth import CurrentUser


class OrderTracking:
    """
    订单追踪服务类
    
    【功能说明】
    1. 根据柜号查询完整的物流追踪信息
    2. 根据用户类型进行权限验证
    3. 构建港前和港后的时间轴数据
    
    【权限验证逻辑】
    - 员工用户（is_staff=True）：直接返回完整信息
    - 客户用户（is_customer=True）：验证柜号归属后返回
    """
    
    def __init__(
        self,
        user: CurrentUser,
        container_number: str,
        db_session: Session,
    ) -> None:
        """
        初始化订单追踪服务
        
        Args:
            user: 当前登录用户
            container_number: 要查询的柜号
            db_session: 数据库会话
        """
        self.user = user
        self.container_number = container_number
        self.db_session = db_session
        self.tz = pytz.timezone("Asia/Shanghai")

    def build_order_full_history(self) -> OrderResponse:
        """
        构建完整的订单追踪历史
        
        【处理流程】
        1. 查询订单基本信息（港前数据）
        2. 验证用户权限（客户用户需验证归属）
        3. 如果有权限，继续构建港后数据
        4. 返回完整的追踪响应
        
        Returns:
            OrderResponse: 完整的订单追踪响应
        """
        try:
            preport, has_permission, order_owner = self._build_preport_history()
            
            if not has_permission:
                return OrderResponse(
                    preport_timenode=None,
                    postport_timenode=None,
                    has_permission=False,
                    message=f"您没有权限查看柜号 {self.container_number} 的详情，该柜子归属于其他客户",
                )
            
            if preport is None:
                return OrderResponse(
                    preport_timenode=None,
                    postport_timenode=None,
                    has_permission=True,
                    message=f"未找到柜号 {self.container_number} 的相关信息",
                )
            
            postport = self._build_postport_history()
            
            return OrderResponse(
                preport_timenode=preport,
                postport_timenode=postport,
                has_permission=True,
                message=None,
            )
        except Exception as e:
            # 捕获所有异常，返回友好提示+打印错误日志
            print(f"Order tracking error: {str(e)}")  # 输出到Azure日志
            raise HTTPException(
                status_code=400,
                detail=f"查询柜号 {self.container_number} 失败：{str(e)}"
            )

    def _build_preport_history(self) -> tuple[Optional[OrderPreportResponse], bool, Optional[str]]:
        """
        构建港前轨迹数据，同时进行权限验证
        
        【权限验证逻辑】
        1. 查询柜号对应的订单
        2. 如果是客户用户，检查订单的 customer_name_id 是否匹配
        3. 员工用户直接通过验证
        
        Returns:
            tuple: (港前数据, 是否有权限, 订单所属客户名称)
        """
        order_data = (
            self.db_session.query(Order)
            .join(Order.container)
            .options(
                joinedload(Order.user),
                joinedload(Order.container),
                joinedload(Order.warehouse),
                joinedload(Order.vessel),
                joinedload(Order.retrieval),
                joinedload(Order.offload),
            )
            .filter(Container.container_number == self.container_number)
            .first()
        )
        
        if not order_data:
            return None, True, None
        
        # 修复：空值判断（order_data.user可能为None）
        order_owner_zem_name = order_data.user.zem_name if (order_data.user and hasattr(order_data.user, 'zem_name')) else None
        
        if self.user.is_customer and order_owner_zem_name != self.user.zem_name:
            return None, False, order_owner_zem_name
        
        order_dict = OrderPreportResponse.model_validate(order_data).model_dump()
        preport_history = []
        pod = None
        
        # 1. 订单创建事件（空值判断）
        if order_dict.get("created_at"):
            preport_history.append({
                "status": "ORDER_CREATED",
                "description": f"创建订单: {order_dict.get('container', {}).get('container_number', '未知柜号')}",
                "timestamp": self._format_date_only(order_dict["created_at"]),
            })
        
        # 2. 港口相关事件（修复：多层级空值判断）
        if order_dict.get("add_to_t49"):
            vessel = order_dict.get("vessel", {})
            pod = vessel.get("destination_port") if vessel else None
            
            retrieval = order_dict.get("retrieval", {})
            if retrieval and retrieval.get("temp_t49_pod_arrive_at"):
                preport_history.append({
                    "status": "ARRIVED_AT_PORT",
                    "description": f"到达港口: {pod or '未知港口'}",
                    "location": pod,
                    "timestamp": self._format_date_only(retrieval["temp_t49_pod_arrive_at"]),
                })
            
            if retrieval and retrieval.get("temp_t49_pod_discharge_at"):
                preport_history.append({
                    "status": "PORT_UNLOADING",
                    "description": "港口卸货",
                    "location": pod,
                    "timestamp": self._format_date_only(retrieval["temp_t49_pod_discharge_at"]),
                })
        
        # 3. 提柜相关事件（修复：空值判断）
        retrieval = order_dict.get("retrieval", {})
        if retrieval:
            if retrieval.get("target_retrieval_timestamp_lower"):
                lower_time = retrieval.get("target_retrieval_timestamp_lower")
                upper_time = retrieval.get("target_retrieval_timestamp")
                if lower_time and upper_time:
                    time_range = f"{self._format_date_only(lower_time)} 到 {self._format_date_only(upper_time)}"
                elif upper_time:
                    time_range = self._format_date_only(upper_time)
                else:
                    time_range = ""
                target_time = self._convert_tz(retrieval.get("target_retrieval_timestamp"))
                preport_history.append({
                    "status": "PORT_PICKUP_SCHEDULED",
                    "description": f"预计提柜时间 {time_range}",
                    "location": pod,
                    "timestamp": self._format_date_only(retrieval["target_retrieval_timestamp_lower"]),
                })
            
            if retrieval.get("actual_retrieval_timestamp"):
                location = retrieval.get("retrieval_destination_precise")
                preport_history.append({
                    "status": "ARRIVE_AT_WAREHOUSE",
                    "description": "提柜完成",
                    "location": location,
                    "timestamp": self._format_date_only(retrieval.get("actual_retrieval_timestamp")),
                })
        
        # 4. 卸货/拆柜事件（修复：空值判断）
        offload = order_dict.get("offload", {})
        retrieval = order_dict.get("retrieval", {})
        if offload:
            if offload.get("offload_at"):
                location = retrieval.get("retrieval_destination_precise") if retrieval else None
                preport_history.append({
                    "status": "OFFLOAD",
                    "description": "拆柜完成",
                    "location": location,
                    "timestamp": self._format_date_only(offload["offload_at"]),
                })
            
            if retrieval and retrieval.get("empty_returned"):
                preport_history.append({
                    "status": "EMPTY_RETURN",
                    "description": "已归还空箱",
                    "timestamp": self._format_date_only(retrieval.get("empty_returned_at")),
                })
        
        order_dict["history"] = preport_history
        return OrderPreportResponse.model_validate(order_dict), True, order_owner_zem_name

    def _build_postport_history(self) -> OrderPostportResponse:
        """
        构建港前轨迹数据，同时进行权限验证
        
        【权限验证逻辑】
        1. 查询柜号对应的订单
        2. 如果是客户用户，检查订单的 customer_name_id 是否匹配
        3. 员工用户直接通过验证
        
        Returns:
            tuple: (港前数据, 是否有权限, 订单所属客户名称)
        """
        try:
            print(f"[Postport] 查询柜号: {self.container_number}")
            
            # 1. 先查询所有 pallet 的异常信息
            pallet_exceptions = {}
            exceptions_query = (
                self.db_session.query(
                    Pallet.id,
                    PalletException.exception_type,
                    PalletException.exception_reason
                )
                .select_from(Pallet)
                .join(Pallet.container)
                .outerjoin(PalletException, PalletException.pallet_id == Pallet.id)
                .filter(Container.container_number == self.container_number)
                .filter(PalletException.id.isnot(None))
                .all()
            )
            print(f"[Postport] 异常查询结果行数: {len(exceptions_query)}")
            # 按 pallet id 保存异常信息（如果有多个异常，取第一个）
            for exc_row in exceptions_query:
                pallet_id = exc_row[0]
                print(f"[Postport] 异常数据 - pallet_id: {pallet_id}, type: {exc_row[1]}, reason: {exc_row[2]}")
                if pallet_id not in pallet_exceptions:
                    pallet_exceptions[pallet_id] = {
                        'exception_type': exc_row[1],
                        'exception_reason': exc_row[2]
                    }
            print(f"[Postport] pallet_exceptions dict: {pallet_exceptions}")
            
            # 2. 查询基础的港后数据
            base_query = (
                self.db_session.query(
                    Pallet.destination,
                    Pallet.PO_ID,
                    Pallet.delivery_method,
                    Pallet.note,
                    Pallet.delivery_type,
                    Shipment.shipment_batch_number,
                    Shipment.is_shipment_schduled,
                    Shipment.shipment_appointment_utc.label("shipment_schduled_at"),
                    Shipment.shipment_appointment_utc.label("shipment_appointment"),
                    Shipment.is_shipped,
                    Shipment.shipped_at.label("shipped_at"),
                    Shipment.is_arrived,
                    Shipment.arrived_at.label("arrived_at"),
                    Shipment.pod_link,
                    Shipment.pod_uploaded_at,
                    Shipment.shipping_order_link,
                    Shipment.appointment_id,
                    Pallet.id.label("pallet_id"),  # 新增：单独查询 pallet_id
                    func.round(cast(func.coalesce(Pallet.cbm, 0), Numeric), 4).label("cbm"),
                    func.round(
                        cast(func.coalesce(Pallet.weight_lbs, 0) / 2.20462, Numeric), 2
                    ).label("weight_kg"),
                    Pallet.pcs.label("pcs"),
                )
                .join(Pallet.container)
                .outerjoin(Pallet.shipment)
                .filter(Container.container_number == self.container_number)
                .all()
            )
            print(f"[Postport] base_query 结果行数: {len(base_query)}")
            
            # 3. 手动分组（按原始的分组键）
            grouped_data = {}
            for row in base_query:
                # 分组键：destination、PO_ID、delivery_method、note、delivery_type、shipment_batch_number、is_shipment_schduled、shipment_appointment_utc、is_shipped、shipped_at_utc、is_arrived、arrived_at_utc、pod_link、pod_uploaded_at、shipping_order_link、appointment_id
                key = (
                    row[0],  # destination
                    row[1],  # PO_ID
                    row[2],  # delivery_method
                    row[3],  # note
                    row[4],  # delivery_type
                    row[5],  # shipment_batch_number
                    row[6],  # is_shipment_schduled
                    row[7],  # shipment_schduled_at (which is shipment_appointment_utc)
                    row[8],  # shipment_appointment (which is also shipment_appointment_utc)
                    row[9],  # is_shipped
                    row[10], # shipped_at
                    row[11], # is_arrived
                    row[12], # arrived_at
                    row[13], # pod_link
                    row[14], # pod_uploaded_at
                    row[15], # shipping_order_link
                    row[16], # appointment_id
                )
                
                pallet_id = row[17]  # 第18个元素是 pallet_id
                if key not in grouped_data:
                    grouped_data[key] = {
                        'base_row': row,
                        'pallet_ids': set(),
                        'total_cbm': 0.0,
                        'total_weight': 0.0,
                        'total_pcs': 0,
                    }
                grouped_data[key]['pallet_ids'].add(pallet_id)
                grouped_data[key]['total_cbm'] += float(row[18]) if row[18] else 0
                grouped_data[key]['total_weight'] += float(row[19]) if row[19] else 0
                grouped_data[key]['total_pcs'] += int(row[20]) if row[20] else 0
            
            print(f"[Postport] 分组后组数: {len(grouped_data)}")
            
        except Exception as e:
            print(f"Postport query error: {str(e)}")
            import traceback
            traceback.print_exc()
            return OrderPostportResponse(shipment=[])
        
        data = []
        for row_idx, (key, group) in enumerate(grouped_data.items()):
            row = group['base_row']
            pallet_ids = group['pallet_ids']
            n_pallet = len(pallet_ids)
            
            # 检查是否有异常
            has_exception = False
            exception_type = None
            exception_reason = None
            print(f"[Postport] 第 {row_idx} 组数据 - pallet_ids: {list(pallet_ids)}")
            for pid in pallet_ids:
                if pid in pallet_exceptions:
                    has_exception = True
                    exception_type = pallet_exceptions[pid]['exception_type']
                    exception_reason = pallet_exceptions[pid]['exception_reason']
                    print(f"[Postport]   找到异常! pid={pid}, type={exception_type}")
                    break
            
            data.append(
                PalletShipmentSummary(
                    destination=row[0],
                    PO_ID=row[1],
                    delivery_method=row[2],
                    note=row[3],
                    delivery_type=row[4],
                    master_shipment_batch_number=row[5],
                    is_shipment_schduled=row[6],
                    shipment_schduled_at=row[7],
                    shipment_appointment=row[8],
                    is_shipped=row[9],
                    shipped_at=row[10],
                    is_arrived=row[11],
                    arrived_at=row[12],
                    pod_link=row[13],
                    pod_uploaded_at=row[14],
                    shipping_order_link=row[15],
                    appointment_id=row[16],
                    cbm=round(group['total_cbm'], 4),
                    weight_kg=round(group['total_weight'], 2),
                    n_pallet=n_pallet,
                    pcs=group['total_pcs'],
                    has_exception=has_exception,
                    exception_type=exception_type,
                    exception_reason=exception_reason,
                )
            )
        
        return OrderPostportResponse(shipment=data)

    def _convert_tz(self, ts: datetime) -> Optional[datetime]:
        """
        将 UTC 时间转换为上海时区
        
        Args:
            ts: UTC 时间戳
        
        Returns:
            转换后的时间（不带时区信息）
        """
        if not ts:
            return None
        try:
            # 如果ts没有tzinfo，先添加UTC时区
            if ts.tzinfo is None:
                ts = pytz.UTC.localize(ts)
            return ts.astimezone(self.tz).replace(tzinfo=None)
        except Exception as e:
            print(f"Timezone convert error: {str(e)}")
            return ts  # 转换失败时返回原时间
        
    def _format_date_only(self, ts: datetime) -> str:
        """
        格式化日期（仅显示日期，不显示时间）
        
        Args:
            ts: 时间戳
        
        Returns:
            格式化后的日期字符串
        """
        if not ts:
            return ""
        try:
            return ts.strftime("%Y-%m-%d")
        except Exception as e:
            print(f"Date format error: {str(e)}")
            return ""