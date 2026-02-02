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
        # 使用上海时区进行时间转换
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
        # 首先进行权限验证和港前数据查询
        preport, has_permission, order_owner = self._build_preport_history()
        
        # 【权限判断】
        if not has_permission:
            # 客户无权限查看此柜号
            return OrderResponse(
                preport_timenode=None,
                postport_timenode=None,
                has_permission=False,
                message=f"您没有权限查看柜号 {self.container_number} 的详情，该柜子归属于其他客户",
            )
        
        # 如果柜号不存在
        if preport is None:
            return OrderResponse(
                preport_timenode=None,
                postport_timenode=None,
                has_permission=True,
                message=f"未找到柜号 {self.container_number} 的相关信息",
            )
        
        # 构建港后数据
        postport = self._build_postport_history()
        
        return OrderResponse(
            preport_timenode=preport,
            postport_timenode=postport,
            has_permission=True,
            message=None,
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
        # 查询订单数据，关联加载所有相关信息
        order_data = (
            self.db_session.query(Order)
            .join(Order.container)
            .options(
                joinedload(Order.user),      # 关联客户信息
                joinedload(Order.container), # 关联集装箱信息
                joinedload(Order.warehouse), # 关联仓库信息
                joinedload(Order.vessel),    # 关联船舶信息
                joinedload(Order.retrieval), # 关联提柜信息
                joinedload(Order.offload),   # 关联卸货信息
            )
            .filter(Container.container_number == self.container_number)
            .first()
        )
        
        # 柜号不存在
        if not order_data:
            return None, True, None
        
        # 获取订单所属客户信息
        order_owner_zem_name = order_data.user.zem_name if order_data.user else None
        
        # 【权限验证】
        # 员工用户：无需验证，直接通过
        # 客户用户：需验证柜号归属
        if self.user.is_customer:
            # 客户用户必须验证柜号归属
            if order_owner_zem_name != self.user.zem_name:
                # 归属不匹配，无权限查看
                return None, False, order_owner_zem_name
        
        # 有权限，构建港前轨迹数据
        order_dict = OrderPreportResponse.model_validate(order_data).model_dump()
        preport_history = []
        pod = None  # 目的港口
        
        # 1. 订单创建事件
        if order_dict["created_at"]:
            preport_history.append({
                "status": "ORDER_CREATED",
                "description": f"创建订单: {order_dict['container']['container_number']}",
                "timestamp": self._convert_tz(order_dict["created_at"]),
            })
        
        # 2. 港口相关事件（需要 T49 追踪）
        if order_dict["add_to_t49"]:
            pod = order_dict["vessel"]["destination_port"] if order_dict["vessel"] else None
            
            # 到达港口
            if order_dict["retrieval"] and order_dict["retrieval"]["temp_t49_pod_arrive_at"]:
                preport_history.append({
                    "status": "ARRIVED_AT_PORT",
                    "description": f"到达港口: {pod}",
                    "location": pod,
                    "timestamp": self._convert_tz(order_dict["retrieval"]["temp_t49_pod_arrive_at"]),
                })
            
            # 港口卸货
            if order_dict["retrieval"] and order_dict["retrieval"]["temp_t49_pod_discharge_at"]:
                preport_history.append({
                    "status": "PORT_UNLOADING",
                    "description": "港口卸货",
                    "location": pod,
                    "timestamp": self._convert_tz(order_dict["retrieval"]["temp_t49_pod_discharge_at"]),
                })
        
        # 3. 提柜相关事件
        if order_dict["retrieval"]:
            retrieval = order_dict["retrieval"]
            
            # 预约提柜
            if retrieval["scheduled_at"]:
                target_time = self._convert_tz(retrieval["target_retrieval_timestamp"])
                preport_history.append({
                    "status": "PORT_PICKUP_SCHEDULED",
                    "description": f"预约港口提柜: 预计提柜时间 {target_time}",
                    "location": pod,
                    "timestamp": self._convert_tz(retrieval["scheduled_at"]),
                })
            
            # 到达仓库
            if retrieval["arrive_at_destination"]:
                preport_history.append({
                    "status": "ARRIVE_AT_WAREHOUSE",
                    "description": f"港口提柜完成, 货柜到达目的仓点 {retrieval['retrieval_destination_precise']}",
                    "location": retrieval["retrieval_destination_precise"],
                    "timestamp": self._convert_tz(retrieval["arrive_at"]),
                })
        
        # 4. 卸货/拆柜事件
        if order_dict["offload"]:
            offload = order_dict["offload"]
            retrieval = order_dict["retrieval"]
            
            # 拆柜完成
            if offload["offload_at"]:
                location = retrieval["retrieval_destination_precise"] if retrieval else None
                preport_history.append({
                    "status": "OFFLOAD",
                    "description": "拆柜完成",
                    "location": location,
                    "timestamp": self._convert_tz(offload["offload_at"]),
                })
            
            # 空箱归还
            if retrieval and retrieval["empty_returned"]:
                preport_history.append({
                    "status": "EMPTY_RETURN",
                    "description": "已归还空箱",
                    "timestamp": self._convert_tz(retrieval["empty_returned_at"]),
                })
        
        order_dict["history"] = preport_history
        return OrderPreportResponse.model_validate(order_dict), True, order_owner_zem_name

    def _build_postport_history(self) -> OrderPostportResponse:
        """
        构建港后轨迹数据
        
        查询托盘运输批次信息，按目的地和 PO_ID 分组汇总
        
        Returns:
            OrderPostportResponse: 港后轨迹响应
        """
        try:
            # 查询托盘运输批次数据
            results = (
                self.db_session.query(
                    Pallet.destination,
                    Pallet.PO_ID,
                    Pallet.delivery_method,
                    Pallet.note,
                    Pallet.delivery_type,
                    Shipment.shipment_batch_number,
                    Shipment.is_shipment_schduled,
                    Shipment.shipment_schduled_at,
                    Shipment.shipment_appointment_utc.label("shipment_appointment"),
                    Shipment.is_shipped,
                    Shipment.shipped_at_utc.label("shipped_at"),
                    Shipment.is_arrived,
                    Shipment.arrived_at_utc.label("arrived_at"),
                    Shipment.pod_link,
                    Shipment.pod_uploaded_at,
                    func.round(cast(func.sum(Pallet.cbm), Numeric), 4).label("cbm"),
                    func.round(
                        cast(func.sum(Pallet.weight_lbs) / 2.20462, Numeric), 2
                    ).label("weight_kg"),
                    func.count(distinct(Pallet.id)).label("n_pallet"),
                    func.count(Pallet.pcs).label("pcs"),
                )
                .join(Pallet.container)
                .outerjoin(Pallet.shipment)
                .filter(Container.container_number == self.container_number)
                .group_by(
                    Pallet.destination,
                    Pallet.PO_ID,
                    Pallet.delivery_method,
                    Pallet.note,
                    Pallet.delivery_type,
                    Shipment.shipment_batch_number,
                    Shipment.is_shipment_schduled,
                    Shipment.shipment_schduled_at,
                    Shipment.shipment_appointment_utc,
                    Shipment.is_shipped,
                    Shipment.shipped_at_utc,
                    Shipment.is_arrived,
                    Shipment.arrived_at_utc,
                    Shipment.pod_link,
                    Shipment.pod_uploaded_at,
                )
                .all()
            )
        except Exception as e:
            # 查询异常时返回空的港后数据
            return OrderPostportResponse(shipment=[])
        
        # 构建运输批次汇总数据
        data = [
            PalletShipmentSummary(
                destination=row[0],
                PO_ID=row[1],
                delivery_method=row[2],
                note=row[3],
                delivery_type=row[4],
                master_shipment_batch_number=row[5],
                is_shipment_schduled=row[6],
                shipment_schduled_at=self._convert_tz(row[7]),
                shipment_appointment=self._convert_tz(row[8]),
                is_shipped=row[9],
                shipped_at=self._convert_tz(row[10]),
                is_arrived=row[11],
                arrived_at=self._convert_tz(row[12]),
                pod_link=row[13],
                pod_uploaded_at=self._convert_tz(row[14]),
                cbm=row[15],
                weight_kg=row[16],
                n_pallet=row[17],
                pcs=row[18],
            )
            for row in results
        ]
        
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
            return ts
        return ts.astimezone(self.tz).replace(tzinfo=None)
