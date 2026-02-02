"""
登录相关的请求/响应数据模型

【登录验证逻辑说明】
1. 用户提交 username 和 password
2. 后端优先查询 Customer 表（客户用户）
3. 若 Customer 表无该用户，查询 AuthUser 表（员工用户）
4. 验证成功后返回 JWT token，包含用户类型信息
"""
from pydantic import BaseModel
from typing import Literal


class LoginRequest(BaseModel):
    """
    登录请求模型
    
    Attributes:
        username: 用户名
        password: 密码
    """
    username: str
    password: str


class UserAuth(BaseModel):
    """
    登录成功响应模型
    
    Attributes:
        user: 用户显示名称（客户为 zem_name，员工为 username）
        access_token: JWT 访问令牌
        user_type: 用户类型 - "customer"（客户）或 "staff"（员工）
    
    【用户类型说明】
    - customer: 来自 warehouse_customer 表的客户用户，查询柜号时需验证归属
    - staff: 来自 auth_user 表的员工用户，查询柜号时无需验证归属
    """
    user: str
    access_token: str
    user_type: Literal["customer", "staff"]


class TokenPayload(BaseModel):
    """
    JWT Token 载荷模型
    用于解码 token 后的数据结构
    
    Attributes:
        user_name: 用户名（用于数据库查询）
        display_name: 用户显示名称
        user_type: 用户类型
    """
    user_name: str
    display_name: str
    user_type: Literal["customer", "staff"]
