from typing import Any
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Create the SQLAlchemy asynchronous engine
engine_kwargs: dict[str, Any] = {
    "echo": False,
    "future": True,
}
if "postgresql" in settings.DATABASE_URL:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Create a sessionmaker configured to return AsyncSession instances
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.
    
    This ensures that each request gets its own separate database session.
    The session is automatically closed (and returned to the pool) after the
    request finishes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # We don't explicitly need to close here since `async with` handles it,
            # but using try/finally ensures no connections leak in case of exceptions.
            pass
