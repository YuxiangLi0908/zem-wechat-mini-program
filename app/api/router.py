"""
API 路由配置模块

汇总所有 API 端点，包括：
- 健康检查接口
- 登录接口
- 柜号查询接口
"""
from fastapi import APIRouter

from app.api import heartbeat, login, order_tracking

api_router = APIRouter()

# 健康检查接口（无需认证）
api_router.include_router(heartbeat.router, tags=["health"])

# 登录接口（无需认证）
api_router.include_router(login.router, tags=["login"])

# 柜号查询接口（需要 Bearer Token 认证）
api_router.include_router(order_tracking.router, tags=["order_tracking"])
