"""
数据库连接和会话管理
使用SQLAlchemy ORM进行数据库操作
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings


# 创建数据库引擎
# SQLite需要设置check_same_thread=False以支持多线程
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=settings.DEBUG,
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    用于FastAPI依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库表结构
    在应用启动时调用
    """
    from app.models import Base
    Base.metadata.create_all(bind=engine)


def get_db_path() -> Path:
    """获取数据库文件路径"""
    db_path = Path(settings.DATABASE_PATH)
    if not db_path.is_absolute():
        db_path = project_root / settings.DATABASE_PATH
    return db_path
