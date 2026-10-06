import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from cache_service.config import Settings
from cache_service.database import create_engine

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else Settings()
    engine = create_engine(configuration)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Persistent caching service", lifespan=lifespan)

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready() -> dict[str, str]:
        try:
            async with engine.connect() as connection:
                # Check the migrated schema as well as database connectivity.
                await connection.execute(text("SELECT id FROM payloads LIMIT 0"))
                await connection.execute(text("SELECT source_digest FROM transformations LIMIT 0"))
        except (SQLAlchemyError, TimeoutError, OSError) as exc:
            logger.warning("Database readiness check failed: %s", type(exc).__name__)
            raise HTTPException(status_code=503, detail="Database is not ready") from exc
        return {"status": "ok"}

    return app
