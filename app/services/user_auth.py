"""
用户认证服务模块

提供 JWT token 验证和当前用户获取功能

【核心功能】
1. 从请求头解析 Bearer token
2. 验证 token 有效性
3. 根据 user_type 从对应表中获取用户信息
4. 返回用户信息供业务逻辑使用

【用户类型处理】
- customer: 从 Customer 表获取用户信息
- staff: 从 AuthUser 表获取用户信息
"""
from typing import Union

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.data_models.db.user import Customer, AuthUser
from app.data_models.login import TokenPayload
from app.services.config import app_config
from app.services.db_session import db_session

# OAuth2 密码模式，token 获取端点为 /login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class CurrentUser:
    """
    当前登录用户信息封装类
    
    【设计说明】
    由于客户和员工来自不同的表，使用此类统一封装用户信息
    便于业务逻辑根据 user_type 进行权限判断
    
    Attributes:
        username: 用户名
        display_name: 显示名称
        user_type: 用户类型 ("customer" 或 "staff")
        customer: 客户实体（仅当 user_type="customer" 时有值）
        staff: 员工实体（仅当 user_type="staff" 时有值）
    """
    def __init__(
        self,
        username: str,
        display_name: str,
        user_type: str,
        customer: Customer = None,
        staff: AuthUser = None,
    ):
        self.username = username
        self.display_name = display_name
        self.user_type = user_type
        self.customer = customer
        self.staff = staff
    
    @property
    def is_customer(self) -> bool:
        """判断是否为客户用户"""
        return self.user_type == "customer"
    
    @property
    def is_staff(self) -> bool:
        """判断是否为员工用户"""
        return self.user_type == "staff"
    
    @property
    def zem_name(self) -> str:
        """
        获取客户的 zem_name（用于权限验证）
        
        【权限验证关键】
        只有客户用户才有 zem_name，用于验证柜号归属
        员工用户返回空字符串，表示可查看所有柜号
        """
        if self.customer:
            return self.customer.zem_name
        return ""


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(db_session.get_db),
) -> CurrentUser:
    """
    从 JWT token 获取当前登录用户
    
    【处理流程】
    1. 解码并验证 JWT token
    2. 从 token 中提取用户名和用户类型
    3. 根据用户类型从对应表中查询用户实体
    4. 返回封装的 CurrentUser 对象
    
    Args:
        token: Bearer token（由 OAuth2PasswordBearer 自动从请求头提取）
        db: 数据库会话
    
    Returns:
        CurrentUser: 当前登录用户信息
    
    Raises:
        HTTPException: 401 - token 无效或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 解码 JWT token
        payload = jwt.decode(
            token, app_config.SECRET_KEY, algorithms=[app_config.JWT_ALGO]
        )
        username: str = payload.get("user_name")
        user_type: str = payload.get("user_type")
        display_name: str = payload.get("display_name", username)
        
        if username is None or user_type is None:
            raise credentials_exception
            
    except PyJWTError:
        raise credentials_exception
    
    # 【关键逻辑】根据用户类型从对应表获取用户实体
    if user_type == "customer":
        # 客户用户：从 Customer 表获取
        customer = db.query(Customer).filter(Customer.username == username).first()
        if customer is None:
            raise credentials_exception
        return CurrentUser(
            username=username,
            display_name=display_name,
            user_type=user_type,
            customer=customer,
        )
    elif user_type == "staff":
        # 员工用户：从 AuthUser 表获取
        staff = db.query(AuthUser).filter(AuthUser.username == username).first()
        if staff is None:
            raise credentials_exception
        return CurrentUser(
            username=username,
            display_name=display_name,
            user_type=user_type,
            staff=staff,
        )
    else:
        raise credentials_exception
