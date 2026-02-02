"""
应用配置模块

存储应用级别的配置信息，包括：
- JWT 密钥和算法
- 数据库连接信息
- 其他环境变量
"""
import os


class AppConfig:
    """
    应用配置类
    
    【环境变量说明】
    - JWT_SECRET_KEY: JWT 签名密钥（必须与 zem-client-svc 一致）
    - ENV: 环境标识（local/production）
    - DBUSER/DBPASS/DBHOST/DBPORT/DBNAME: 生产环境数据库配置
    - POSTGRESQL_PWD: 本地开发环境 PostgreSQL 密码
    """
    def __init__(self) -> None:
        # JWT 配置
        self.JWT_ALGO = "HS256"
        self.SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "test-secret-key")


app_config = AppConfig()
