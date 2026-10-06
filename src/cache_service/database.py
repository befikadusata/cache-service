from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from cache_service.config import Settings
from cache_service.coordination import Coordination


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        execution_options={"cache_coordination": Coordination(settings)},
        pool_size=settings.pool_size,
        max_overflow=0,
        pool_timeout=settings.pool_timeout_seconds,
        pool_pre_ping=True,
        isolation_level="READ COMMITTED",
        connect_args={
            "timeout": settings.database_connect_timeout_seconds,
            "server_settings": {
                "statement_timeout": str(
                    max(1, int(settings.database_statement_timeout_seconds * 1000))
                ),
            },
        },
    )
