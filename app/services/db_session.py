"""
数据库会话管理模块

提供数据库连接和会话管理功能
支持本地开发和生产环境两种配置
"""
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class DBSession:
    """
    数据库会话管理类
    
    【环境配置说明】
    - 生产环境（ENV=production）：使用 DBUSER/DBPASS/DBHOST/DBPORT/DBNAME 环境变量
    - 本地开发环境：使用本地 PostgreSQL，密码从 POSTGRESQL_PWD 环境变量读取
    
    【与 zem-client-svc 的一致性】
    配置逻辑与 zem-client-svc 完全一致，确保连接同一数据库
    """
    def __init__(self) -> None:
        if os.environ.get("ENV", "local") == "production":
            # 生产环境配置
            self.user = os.environ.get("DBUSER")
            self.password = os.environ.get("DBPASS")
            self.host = os.environ.get("DBHOST")
            self.port = int(os.environ.get("DBPORT", "5432"))
            self.database = os.environ.get("DBNAME")
        else:
            # 本地开发环境配置
            self.user = "postgres"
            self.password = os.environ.get("POSTGRESQL_PWD")
            self.host = "127.0.0.1"
            self.port = 5432
            self.database = "zem"
        
        self.database_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def get_db(self) -> Generator[Session, None, None]:
        """
        获取数据库会话的生成器
        用于 FastAPI 的依赖注入
        
        Yields:
            Session: SQLAlchemy 数据库会话
        """
        engine = create_engine(self.database_url)
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = session_local()
        try:
            yield db
        finally:
            db.close()


# 全局数据库会话实例
db_session = DBSession()
