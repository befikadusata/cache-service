"""Versioned successful-result caching with short PostgreSQL transactions."""

from collections.abc import Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncEngine

from cache_service.identity import transformation_identity
from cache_service.transformation import Transformer

_READ_BATCH_SIZE = 500


class TransformationFailed(RuntimeError):
    """The replaceable transformer failed before publication."""


class DatabaseUnavailable(RuntimeError):
    """Database connection establishment exceeded its own timeout."""


async def cached_transformations(
    engine: AsyncEngine, sources: Sequence[str], transformer: Transformer, version: str
) -> dict[str, str]:
    """Reuse verified rows, deduplicate misses and commit each successful result."""
    identities = {
        source: transformation_identity(source, version=version)
        for source in dict.fromkeys(sources)
    }
    if not identities:
        return {}
    # Index by digest only for lookup; retained source and version establish equality.
    by_digest = {}
    for identity in identities.values():
        previous = by_digest.get(identity.source_digest)
        if previous is not None:
            identity.verify_stored(previous.version, previous.source)
        by_digest[identity.source_digest] = identity

    results: dict[str, str] = {}
    digests = list(by_digest)
    batch_lookup = text(
        "SELECT version, source_digest, source, result FROM transformations "
        "WHERE version = :version AND source_digest IN :digests"
    ).bindparams(bindparam("digests", expanding=True))
    try:
        async with engine.connect() as connection:
            for start in range(0, len(digests), _READ_BATCH_SIZE):
                query = await connection.execute(
                    batch_lookup,
                    {"version": version, "digests": digests[start : start + _READ_BATCH_SIZE]},
                )
                for row in query.mappings():
                    identity = by_digest[row["source_digest"]]
                    identity.verify_stored(row["version"], row["source"])
                    results[identity.source] = row["result"]
    except TimeoutError as exc:
        raise DatabaseUnavailable("Database unavailable") from exc

    for source, identity in identities.items():
        if source in results:
            continue
        # No checked-out connection or transaction spans the external operation.
        try:
            result = await transformer(source)
        except TimeoutError:
            raise
        except Exception as exc:
            raise TransformationFailed("Transformation failed") from exc

        parameters = {"version": version, "digest": identity.source_digest}
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "INSERT INTO transformations (version, source_digest, source, result) "
                        "VALUES (:version, :digest, :source, :result) "
                        "ON CONFLICT (version, source_digest) DO NOTHING"
                    ),
                    {**parameters, "source": source, "result": result},
                )
                # A new READ COMMITTED statement sees a concurrent insert's winner.
                query = await connection.execute(
                    text(
                        "SELECT version, source, result FROM transformations "
                        "WHERE version = :version AND source_digest = :digest"
                    ),
                    parameters,
                )
                stored = query.mappings().one()
                identity.verify_stored(stored["version"], stored["source"])
            results[source] = stored["result"]
        except TimeoutError as exc:
            raise DatabaseUnavailable("Database unavailable") from exc
    return results
