"""
登录接口模块

【关键业务规则】
1. 登录验证顺序：
   - 优先查询 Customer 表（客户用户）
   - 若 Customer 表无该用户，查询 AuthUser 表（员工用户）
   
2. 密码验证：
   - 使用 Django 的 PBKDF2-SHA256 算法验证密码
   - 与 zem-client-svc 保持一致
   
3. Token 生成：
   - 生成 JWT token，包含用户名、显示名称、用户类型
   - 用户类型用于后续权限判断
"""
import jwt
import logging
from typing import Any, Type

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool  # 核心：异步执行同步DB操作

from app.data_models.db.user import Customer, AuthUser
from app.data_models.login import LoginRequest, UserAuth
from app.services.config import app_config
from app.services.db_session import db_session

# 配置日志，方便Azure容器查看真实错误
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
# 全局复用密码验证上下文，避免重复创建
pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"], deprecated="auto")


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """密码验证（兼容空密码/异常格式）"""
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError) as e:
        logger.error(f"Password verify error: {str(e)}")
        return False


def _query_user_sync(db: Session, model: Type[Any], attr: str, value: str):
    """同步查询用户（仅捕获字段不存在异常，暴露真实DB错误）"""
    try:
        # 验证模型字段是否存在
        column = getattr(model, attr)
        # 执行查询（和你的Customer模型字段完全匹配）
        return db.query(model).filter(column == value).first()
    except AttributeError as e:
        # 字段不存在时返回明确错误
        logger.error(f"Model field error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model {model.__name__} has no field: {attr}",
        )
    except Exception as e:
        # 打印真实错误到Azure日志（关键！）
        logger.error(f"Database query error: {str(e)}")
        # 不再返回模糊的503，而是具体错误（调试阶段）
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}",
        )


@router.post("/login", response_model=UserAuth, name="login")
async def login(
    request: LoginRequest,
    db: Session = Depends(db_session.get_db)
) -> UserAuth:
    """
    用户登录接口（修复核心问题：异步执行同步DB查询+正确字段匹配）
    """
    # 1. 基础参数校验
    if not request.username or not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )
    username = request.username.strip()
    password = request.password

    # 2. 【核心修复】异步执行同步查询（解决503的关键）
    # 步骤1：优先查询Customer表（用username字段，和模型一致）
    try:
        customer = await run_in_threadpool(_query_user_sync, db, Customer, "username", username)
    except HTTPException as e:
        # 透传字段/查询异常
        raise e
    except Exception as e:
        logger.error(f"Customer query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        )

    if customer:
        # 客户登录必须验证密码（原代码漏了！）
        if not _verify_password(password, customer.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials / 密码错误",
            )
        # 生成Token（字段和你的Customer模型完全匹配）
        display_name = customer.full_name or customer.zem_name
        token = jwt.encode(
            {
                "user_name": customer.username or customer.zem_name,
                "display_name": display_name,
                "user_type": "customer",
            },
            app_config.SECRET_KEY,
            algorithm=app_config.JWT_ALGO,
        )
        return UserAuth(
            user=display_name,
            access_token=token,
            user_type="customer",
        )

    # 3. 步骤2：查询AuthUser表（员工用户）
    try:
        staff = await run_in_threadpool(_query_user_sync, db, AuthUser, "username", username)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"AuthUser query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        )

    if staff:
        # 检查员工账户是否激活
        if not getattr(staff, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled / 账户已禁用",
            )
        # 验证密码
        if not _verify_password(password, staff.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials / 密码错误",
            )
        # 生成员工Token
        display_name = f"{staff.first_name} {staff.last_name}".strip() or staff.username
        token = jwt.encode(
            {
                "user_name": staff.username,
                "display_name": display_name,
                "user_type": "staff",
            },
            app_config.SECRET_KEY,
            algorithm=app_config.JWT_ALGO,
        )
        return UserAuth(
            user=display_name,
            access_token=token,
            user_type="staff",
        )

    # 4. 两个表都无该用户
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found / 用户不存在",
    )