"""数据库连接配置"""
from contextlib import asynccontextmanager
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

# 创建数据库引擎
engine = create_engine(settings.database_url, echo=settings.debug)


def init_db() -> None:
    """初始化数据库，创建所有表"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """获取数据库会话（同步版本）"""
    with Session(engine) as session:
        yield session


# 缓存异步 session 类
_async_session = None

def _get_async_session():
    """获取或创建异步 Session 类"""
    global _async_session
    if _async_session is None:
        from sqlmodel import sessionmaker
        _async_session = sessionmaker(engine, class_=Session, expire_on_commit=False)
    return _async_session


@asynccontextmanager
async def async_session():
    """异步数据库会话上下文管理器"""
    async_session = _get_async_session()
    async with async_session() as session:
        yield session
