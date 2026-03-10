"""
SQLite database setup with async SQLAlchemy.

Uses WAL mode for concurrent reads from 50 sales reps.
Single file: crm.db on the owner's laptop.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

from app.core.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={
        "check_same_thread": False,  # Required for SQLite + async
    },
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode and performance optimizations for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")       # Concurrent reads while writing
    cursor.execute("PRAGMA synchronous=NORMAL")      # Good balance of speed/safety
    cursor.execute("PRAGMA cache_size=-64000")        # 64MB cache
    cursor.execute("PRAGMA foreign_keys=ON")          # Enforce FK constraints
    cursor.execute("PRAGMA busy_timeout=5000")        # Wait 5s on lock instead of failing
    cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency injection for FastAPI routes."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
