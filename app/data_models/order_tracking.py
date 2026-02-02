"""
柜号查询相关的请求/响应数据模型

【数据结构说明】
1. 港前轨迹（Preport）：订单创建 -> 到达港口 -> 提柜 -> 到达仓库 -> 拆柜
2. 港后轨迹（Postport）：托盘运输批次信息，包括调度、发货、送达状态

【响应格式】
与 zem-client-svc 保持一致，返回完整的订单追踪信息
"""
from datetime import date, datetime
from typing import Any, Optional, List

from pydantic import BaseModel, ConfigDict


class OrderTrackingRequest(BaseModel):
    """
    柜号查询请求模型
    
    Attributes:
        container_number: 集装箱柜号（如：ABCD1234567）
    """
    container_number: str


class UserResponse(BaseModel):
    """
    用户信息响应模型（用于订单关联的客户信息）
    """
    zem_name: str
    full_name: str
    zem_code: str
    email: Optional[str]
    note: Optional[str]
    phone: Optional[str]
    accounting_name: Optional[str]
    address: Optional[str]
    username: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ContainerResponse(BaseModel):
    """
    集装箱信息响应模型
    """
    container_number: str
    container_type: Optional[str]
    weight_lbs: Optional[float]
    is_special_container: Optional[bool]
    note: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WarehouseResponse(BaseModel):
    """
    仓库信息响应模型
    """
    name: str
    address: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class VesselResponse(BaseModel):
    """
    船舶信息响应模型
    """
    vessel_id: Optional[str]
    master_bill_of_lading: Optional[str]
    origin_port: Optional[str]
    destination_port: Optional[str]
    shipping_line: Optional[str]
    vessel: Optional[str]
    voyage: Optional[str]
    vessel_etd: Optional[datetime]
    vessel_eta: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RetrievalResponse(BaseModel):
    """
    提柜信息响应模型
    """
    retrieval_id: Optional[str]
    shipping_order_number: Optional[str]
    master_bill_of_lading: Optional[str]
    retrive_by_zem: Optional[bool]
    retrieval_carrier: Optional[str]
    origin_port: Optional[str]
    destination_port: Optional[str]
    shipping_line: Optional[str]
    retrieval_destination_precise: Optional[str]
    assigned_by_appt: Optional[bool]
    retrieval_destination_area: Optional[str]
    scheduled_at: Optional[datetime]
    target_retrieval_timestamp: Optional[datetime]
    target_retrieval_timestamp_lower: Optional[datetime]
    actual_retrieval_timestamp: Optional[datetime]
    note: Optional[str]
    arrive_at_destination: Optional[bool]
    arrive_at: Optional[datetime]
    empty_returned: Optional[bool]
    empty_returned_at: Optional[datetime]
    temp_t49_lfd: Optional[date]
    temp_t49_available_for_pickup: Optional[bool]
    temp_t49_pod_arrive_at: Optional[datetime]
    temp_t49_pod_discharge_at: Optional[datetime]
    temp_t49_hold_status: Optional[bool]

    model_config = ConfigDict(from_attributes=True)


class OffloadResponse(BaseModel):
    """
    卸货/拆柜信息响应模型
    """
    offload_id: Optional[str]
    offload_required: Optional[bool]
    offload_at: Optional[datetime]
    total_pallet: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class TrackingEvent(BaseModel):
    """
    追踪事件模型（用于时间轴展示）
    
    Attributes:
        status: 状态码（如：ORDER_CREATED, ARRIVED_AT_PORT 等）
        description: 状态描述
        location: 位置信息
        timestamp: 时间戳
    """
    status: str
    description: Optional[str] = None
    location: Optional[str] = None
    timestamp: Optional[Any] = None


class OrderPreportResponse(BaseModel):
    """
    港前轨迹响应模型
    
    包含订单基本信息和港前运输各节点状态
    """
    order_id: Optional[str]
    created_at: datetime
    eta: Optional[date]
    order_type: Optional[str]
    add_to_t49: Optional[bool]
    cancel_notification: Optional[bool]
    cancel_time: Optional[date]
    user: Optional[UserResponse]
    container: Optional[ContainerResponse]
    warehouse: Optional[WarehouseResponse]
    vessel: Optional[VesselResponse]
    retrieval: Optional[RetrievalResponse]
    offload: Optional[OffloadResponse]
    history: Optional[List[TrackingEvent]] = None

    model_config = ConfigDict(from_attributes=True)


class PalletShipmentSummary(BaseModel):
    """
    托盘运输批次汇总模型（用于港后轨迹）
    
    按目的地和 PO_ID 分组汇总托盘运输状态
    """
    destination: Optional[str]
    PO_ID: Optional[str]
    delivery_method: Optional[str] = None
    note: Optional[str] = None
    delivery_type: Optional[str] = None
    master_shipment_batch_number: Optional[str] = None
    is_shipment_schduled: Optional[bool] = None
    shipment_schduled_at: Optional[datetime] = None
    shipment_appointment: Optional[datetime] = None
    is_shipped: Optional[bool] = None
    shipped_at: Optional[datetime] = None
    is_arrived: Optional[bool] = None
    arrived_at: Optional[datetime] = None
    pod_link: Optional[str] = None
    pod_uploaded_at: Optional[datetime] = None
    cbm: Optional[float] = None
    weight_kg: Optional[float] = None
    n_pallet: Optional[int] = None
    pcs: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class OrderPostportResponse(BaseModel):
    """
    港后轨迹响应模型
    
    包含所有托盘运输批次的汇总信息
    """
    shipment: Optional[List[PalletShipmentSummary]] = []


class OrderResponse(BaseModel):
    """
    完整的订单追踪响应模型
    
    Attributes:
        preport_timenode: 港前轨迹信息
        postport_timenode: 港后轨迹信息
        has_permission: 是否有权限查看详情（仅对客户用户有意义）
        message: 附加消息（如权限不足时的提示）
    """
    preport_timenode: Optional[OrderPreportResponse] = None
    postport_timenode: Optional[OrderPostportResponse] = None
    has_permission: bool = True
    message: Optional[str] = None
