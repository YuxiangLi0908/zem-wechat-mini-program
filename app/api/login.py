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
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.data_models.db.user import Customer, AuthUser
from app.data_models.login import LoginRequest, UserAuth
from app.services.config import app_config
from app.services.db_session import db_session


def _verify_password(pwd_context: CryptContext, plain_password: str, hashed_password: str) -> bool:
    """Avoid raising when hash is missing or malformed"""
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def _safe_query_user(db: Session, model: type, username: str):
    """Query user table and convert SQL failures to 503 responses"""
    try:
        return db.query(model).filter(model.username == username).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable, please retry later",
        )

router = APIRouter()


@router.post("/login", response_model=UserAuth, name="login")
async def login(
    request: LoginRequest,
    db: Session = Depends(db_session.get_db)
) -> UserAuth:
    """
    用户登录接口
    
    【登录验证逻辑】（与 zem-client-svc 保持一致，增加员工登录支持）
    1. 优先查询 Customer 表（客户用户）
    2. 若 Customer 表无该用户，查询 AuthUser 表（员工用户）
    3. 验证密码
    4. 生成 JWT token 返回
    
    Args:
        request: 登录请求，包含 username 和 password
        db: 数据库会话
    
    Returns:
        UserAuth: 登录成功响应，包含 user、access_token、user_type
    
    Raises:
        404: 用户不存在
        401: 密码错误
    
    示例请求:
        POST /login
        Content-Type: application/json
        {
            "username": "customer_username",
            "password": "user_password"
        }
    
    示例响应:
        {
            "user": "客户显示名称",
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "user_type": "customer"
        }
    """
    if not request.username or not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )

    username = request.username.strip()
    password = request.password

    # Django PBKDF2-SHA256 密码验证上下文
    pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"], deprecated="auto")

    # 【步骤1】优先查询 Customer 表（客户用户）
    customer = _safe_query_user(db, Customer, username)
    
    if customer:
        # 找到客户用户，验证密码
        if not _verify_password(pwd_context, password, customer.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials / 密码错误"
            )
        

        # 生成 JWT token（客户用户）
        token = jwt.encode(
            {
                "user_name": customer.username,
                "display_name": customer.zem_name,
                "user_type": "customer",
            },
            app_config.SECRET_KEY,
            algorithm=app_config.JWT_ALGO,
        )

        return UserAuth(
            user=customer.zem_name,
            access_token=token,
            user_type="customer",
        )
    
    # 【步骤2】Customer 表无该用户，查询 AuthUser 表（员工用户）
    staff = _safe_query_user(db, AuthUser, username)
    
    if staff:
        # 检查员工账户是否激活
        if not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled / 账户已禁用"
            )
        
        # 验证密码
        if not _verify_password(pwd_context, password, staff.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials / 密码错误"
            )
        
        # 生成 JWT token（员工用户）
        # 员工显示名称：优先使用 first_name + last_name，否则使用 username
        display_name = f"{staff.first_name} {staff.last_name}".strip() or staff.username
        
        token = jwt.encode(
            {
                "user_name": staff.username,
                "display_name": display_name,
                "user_type": "staff",  # 【关键】标记为员工用户
            },
            app_config.SECRET_KEY,
            algorithm=app_config.JWT_ALGO,
        )
        
        return UserAuth(
            user=display_name,
            access_token=token,
            user_type="staff"
        )
    
    # 【步骤3】两个表都不存在该用户
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found / 用户不存在"
    )
