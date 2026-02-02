"""
用户数据模型定义

【关键业务规则】
1. Customer 表（warehouse_customer）：存储客户用户信息
   - 客户登录时优先查询此表
   - 客户查询柜号时需验证归属权限
   
2. AuthUser 表（auth_user）：Django 内置的员工用户表
   - 当 Customer 表中无该用户时，查询此表判定为员工登录
   - 员工登录后可查询所有柜号，无需验证归属

【登录验证顺序】
1. 先查询 Customer 表（客户用户）
2. 若不存在，再查询 AuthUser 表（员工用户）
3. 若都不存在，返回用户不存在错误
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.data_models.db.base import Base


class Customer(Base):
    """
    客户用户表
    对应 Django 模型中的 warehouse_customer 表
    """
    __tablename__ = "warehouse_customer"

    id = Column(Integer, primary_key=True, index=True)
    # zem_name: 客户在系统中的唯一标识名称，用于关联订单归属
    zem_name = Column(String, unique=True, index=True)
    full_name = Column(String)
    zem_code = Column(String)
    email = Column(String)
    note = Column(String)
    phone = Column(String)
    accounting_name = Column(String)
    address = Column(String)
    # username/password: 用于登录验证
    username = Column(String, unique=True)
    password = Column(String)


class AuthUser(Base):
    """
    员工用户表（Django 内置 auth_user 表）
    用于员工登录验证
    
    【权限说明】
    员工用户登录后可查询所有柜号详情，无需验证归属
    """
    __tablename__ = "auth_user"

    id = Column(Integer, primary_key=True, index=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime, nullable=True)
    is_superuser = Column(Boolean, default=False)
    username = Column(String(150), unique=True, nullable=False)
    first_name = Column(String(150), default="")
    last_name = Column(String(150), default="")
    email = Column(String(254), default="")
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    date_joined = Column(DateTime, nullable=False)
