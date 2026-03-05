# backend/app/database.py
"""
Async SQLAlchemy engine and session management.

Provides a DatabaseSessionManager for lifespan-based connection pooling
and a get_db dependency for FastAPI route injection.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseSessionManager:
    """Manages async SQLAlchemy engine and session factory lifecycle."""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def init(self, database_url: str) -> None:
        """Initialise the async engine and session factory."""
        self._engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        """Dispose of the engine and release all connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the session factory, raising if not initialised."""
        if self._sessionmaker is None:
            raise RuntimeError("DatabaseSessionManager is not initialised. Call init() first.")
        return self._sessionmaker


# Global singleton
sessionmanager = DatabaseSessionManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with sessionmanager.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Re-export engine reference for Alembic
engine = None  # Set during lifespan init; Alembic uses its own engine
