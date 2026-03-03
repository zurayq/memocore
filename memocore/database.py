"""
database.py — Async SQLAlchemy engine, session factory, and Base.

Architecture decision: We use the async SQLAlchemy API (create_async_engine +
AsyncSession) so that database I/O never blocks FastAPI's event loop. The
'expire_on_commit=False' setting prevents DetachedInstanceError when
attributes are accessed after a session closes — common in async patterns.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from memocore.config import get_settings

settings = get_settings()

# ------------------------------------------------------------------ #
# Engine
# Architecture decision: pool_pre_ping=True verifies connections before
# checkout, recovering gracefully from database restarts or idle timeouts.
# ------------------------------------------------------------------ #
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,        # log SQL only in debug mode
    pool_pre_ping=True,
    # SQLite does not support multiple concurrent writers by default;
    # connect_args is only applied for SQLite connections.
    connect_args={"check_same_thread": False}
    if "sqlite" in settings.DATABASE_URL
    else {},
)

# Session factory — use async_sessionmaker (SQLAlchemy 2.0+)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def init_db() -> None:
    """Create all tables on startup (development convenience).
    In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:  # type: ignore[return]
    """
    FastAPI dependency that yields an AsyncSession per request.
    The session is automatically closed after the request completes,
    even if an exception is raised.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
