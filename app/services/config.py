"""
应用配置模块

存储应用级别的配置信息
"""
import os


class AppConfig:
    """
    应用配置类
    
    【环境变量说明】
    - JWT_SECRET_KEY: JWT 签名密钥（生产环境必须设置，且需与 zem-client-svc 一致）
    - 其他配置可根据需要添加
    """
    def __init__(self) -> None:
        # JWT 配置 - 算法和密钥
        self.JWT_ALGO = "HS256"
        # 【重要】生产环境必须设置 JWT_SECRET_KEY 环境变量，且与 zem-client-svc 一致
        self.SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "test-secret-key")


app_config = AppConfig()
