import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated, Any
from uuid import UUID

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import MultipleResultsFound, NoResultFound, SQLAlchemyError

from cache_service.cache import DatabaseUnavailable, TransformationFailed
from cache_service.config import Settings
from cache_service.database import create_engine
from cache_service.identity import TRANSFORMER_VERSION, IdentityCollisionError
from cache_service.payloads import (
    create_payload,
    read_payload,
)
from cache_service.schemas import PayloadCreate, PayloadCreated, PayloadOutput
from cache_service.transformation import Transformer, uppercase_transform

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    transformer: Transformer = uppercase_transform,
    transformer_version: str = TRANSFORMER_VERSION,
) -> FastAPI:
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

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> Response:
        # ASCII escaping preserves invalid submitted surrogates in the error envelope.
        return Response(
            content=json.dumps({"detail": jsonable_encoder(exc.errors())}, ensure_ascii=True),
            status_code=422,
            media_type="application/json",
        )

    async def validate_payload(
        body: Annotated[Any, Body(json_schema_extra=PayloadCreate.model_json_schema())],
    ) -> PayloadCreate:
        try:
            return PayloadCreate.model_validate(body, context={"settings": configuration})
        except ValidationError as exc:
            errors = [{**error, "loc": ("body", *error["loc"])} for error in exc.errors()]
            raise RequestValidationError(errors) from exc

    async def operational_error(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, TimeoutError):
            status, detail = 504, "Request timed out"
        elif isinstance(exc, TransformationFailed):
            status, detail = 502, "Transformation failed"
        elif isinstance(exc, (IdentityCollisionError, NoResultFound, MultipleResultsFound)):
            status, detail = 500, "Internal server error"
        elif isinstance(exc, (SQLAlchemyError, DatabaseUnavailable, OSError)):
            status, detail = 503, "Database unavailable"
        else:
            status, detail = 500, "Internal server error"
        logger.warning("Payload operation failed: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status, content={"detail": detail},
            headers={"Retry-After": "1"} if status == 503 else None,
        )

    for error_type in (
        SQLAlchemyError,
        DatabaseUnavailable,
        OSError,
        TimeoutError,
        TransformationFailed,
        IdentityCollisionError,
        Exception,
    ):
        app.add_exception_handler(error_type, operational_error)

    @app.post("/payload", response_model=PayloadCreated)
    @app.post("/payloads", response_model=PayloadCreated, include_in_schema=False)
    async def post_payload(
        payload: Annotated[PayloadCreate, Depends(validate_payload)],
    ) -> PayloadCreated:
        async with asyncio.timeout(configuration.generation_timeout_seconds):
            identifier = await create_payload(engine, payload, transformer, transformer_version)
        return PayloadCreated(id=identifier)

    @app.get("/payload/{id}", response_model=PayloadOutput)
    @app.get("/payloads/{id}", response_model=PayloadOutput, include_in_schema=False)
    async def get_payload(id: UUID) -> PayloadOutput:
        async with asyncio.timeout(configuration.read_timeout_seconds):
            output = await read_payload(engine, id)
        if output is None:
            raise HTTPException(status_code=404, detail="Payload not found")
        return PayloadOutput(output=output)

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
