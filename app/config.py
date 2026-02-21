"""
应用配置文件
包含所有环境变量和配置项
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """应用配置类"""

    # 应用基本配置
    APP_NAME: str = "VPN Distribution System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_PATH: str = "vpn_distribution.db"

    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    # X-ui面板配置
    XUI_BASE_URL: str = "http://35.197.153.209:2053"
    XUI_PANEL_PATH: str = "/panel"
    XUI_USERNAME: str = "keithwy"
    XUI_PASSWORD: str = "k19941030"
    XUI_INBOUND_ID: int = 1  # 默认入站ID

    # 订阅服务配置 (3X-UI订阅端口)
    SUBSCRIPTION_BASE_URL: str = "http://cloudkm.shop"
    SUBSCRIPTION_PATH: str = "/sub"

    # 支付配置 (手动审核模式)
    PAYMENT_MODE: str = "manual"  # manual=手动审核, auto=自动
    ADMIN_CONTACT: str = "QQ: xxxxxx"  # 支付后联系管理员

    # CORS配置
    CORS_ORIGINS: list = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://35.197.153.209:8000",
        "http://cloudkm.shop",
        "https://cloudkm.shop",
    ]

    # 流量同步配置
    TRAFFIC_SYNC_INTERVAL_MINUTES: int = 60

    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        db_path = Path(self.DATABASE_PATH)
        if not db_path.is_absolute():
            db_path = Path(__file__).parent.parent / self.DATABASE_PATH
        return f"sqlite:///{db_path}"

    @property
    def xui_login_url(self) -> str:
        """X-ui登录URL"""
        return f"{self.XUI_BASE_URL}/login"

    @property
    def xui_api_base(self) -> str:
        """X-ui API基础URL"""
        return f"{self.XUI_BASE_URL}/api"

    @property
    def subscription_url_template(self) -> str:
        """订阅链接模板"""
        return f"{self.SUBSCRIPTION_BASE_URL}/sub/{{token}}"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 导出配置实例
settings = get_settings()
