"""数据库连接配置"""
from sqlmodel import SQLModel, create_engine
from app.config import settings

# 创建数据库引擎
engine = create_engine(settings.database_url, echo=settings.debug)


def init_db() -> None:
    """初始化数据库，创建所有表"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """获取数据库会话（同步版本）"""
    from sqlmodel import Session
    with Session(engine) as session:
        yield session
