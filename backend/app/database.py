"""数据库连接配置"""
from contextlib import asynccontextmanager
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

# 创建同步数据库引擎
sync_engine = create_engine(settings.database_url, echo=settings.debug)


def init_db() -> None:
    """初始化数据库，创建所有表"""
    SQLModel.metadata.create_all(sync_engine)


def get_session():
    """获取数据库会话（同步版本）"""
    with Session(sync_engine) as session:
        yield session


# 异步引擎部分
def _make_async_url(url: str) -> str:
    """将同步 SQLite URL 转换为异步版本"""
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url

async_url = _make_async_url(settings.database_url)

# 创建异步数据库引擎
async_engine = create_async_engine(async_url, echo=settings.debug)

# 异步 Session 工厂
_async_session_factory = None

def _get_async_session_factory():
    """获取或创建异步 Session 工厂"""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session_factory


@asynccontextmanager
async def async_session():
    """异步数据库会话上下文管理器"""
    session_factory = _get_async_session_factory()
    async with session_factory() as session:
        yield session
