"""
微信小程序后端主入口

【应用说明】
本后端为微信小程序提供 API 服务，包括：
1. 用户登录验证（支持客户和员工两类用户）
2. 柜号查询（包含权限验证）

【与 zem-client-svc 的关系】
- 共享同一数据库
- 登录和查询逻辑与 zem-client-svc 保持一致
- 新增用户类型区分，支持客户权限验证
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.router import api_router


def custom_openapi():
    """
    自定义 OpenAPI 文档配置
    添加 Bearer Token 认证支持
    """
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Zem WeChat Mini Program API",
        version="1.0.0",
        description="微信小程序后端 API，提供登录和柜号查询功能",
        routes=app.routes,
    )
    # 添加 Bearer Token 认证方案
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    # 为所有接口添加安全要求
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", []).append({"BearerAuth": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(title="Zem WeChat Mini Program", version="1.0.0")

# 跨域中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议配置具体域名
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# GZip 压缩中间件
app.add_middleware(GZipMiddleware)

# 注册 API 路由
app.include_router(api_router)

# 使用自定义 OpenAPI 配置
app.openapi = custom_openapi
