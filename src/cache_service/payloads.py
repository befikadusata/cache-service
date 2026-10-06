"""Complete payload generation and immutable PostgreSQL publication."""

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cache_service.identity import TRANSFORMER_VERSION, payload_identity
from cache_service.schemas import PayloadCreate
from cache_service.transformation import Transformer, compose_output


class TransformationFailed(RuntimeError):
    """The replaceable transformer failed before publication."""


class DatabaseUnavailable(RuntimeError):
    """Database connection establishment exceeded its own timeout."""


async def create_payload(
    engine: AsyncEngine,
    request: PayloadCreate,
    transformer: Transformer,
    version: str = TRANSFORMER_VERSION,
) -> UUID:
    identity = payload_identity(request.list1, request.list2, version=version)
    parameters = {"digest": identity.input_digest}
    lookup = text("SELECT id, canonical_input FROM payloads WHERE input_digest = :digest")
    try:
        async with engine.connect() as connection:
            stored = (await connection.execute(lookup, parameters)).mappings().one_or_none()
    except TimeoutError as exc:
        raise DatabaseUnavailable("Database unavailable") from exc
    if stored is not None:
        identity.verify_stored(stored["canonical_input"])
        return stored["id"]

    # No checked-out connection or transaction spans transformation.
    transformed: list[list[str]] = []
    try:
        for values in (request.list1, request.list2):
            transformed.append([await transformer(value) for value in values])
    except TimeoutError:
        raise
    except Exception as exc:
        raise TransformationFailed("Transformation failed") from exc
    output = compose_output(*transformed)

    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO payloads (id, input_digest, canonical_input, output) "
                    "VALUES (:id, :digest, :canonical, :output) "
                    "ON CONFLICT (input_digest) DO NOTHING"
                ),
                {
                    **parameters,
                    "id": uuid4(),
                    "canonical": identity.canonical_input,
                    "output": output,
                },
            )
            # A separate READ COMMITTED statement sees the winner of a concurrent insert.
            stored = (await connection.execute(lookup, parameters)).mappings().one()
            identity.verify_stored(stored["canonical_input"])
    except TimeoutError as exc:
        raise DatabaseUnavailable("Database unavailable") from exc
    return stored["id"]


async def read_payload(engine: AsyncEngine, identifier: UUID) -> str | None:
    try:
        async with engine.connect() as connection:
            return await connection.scalar(
                text("SELECT output FROM payloads WHERE id = :id"), {"id": identifier}
            )
    except TimeoutError as exc:
        raise DatabaseUnavailable("Database unavailable") from exc
