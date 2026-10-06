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
        parameters = {"version": version, "digest": identity.source_digest}
        lookup = text(
            "SELECT version, source, result FROM transformations "
            "WHERE version = :version AND source_digest = :digest"
        )
        transforming = False
        try:
            async with engine.connect() as connection:
                try:
                    # Session ownership survives commit; acquire only once on this connection.
                    async with connection.begin():
                        await connection.execute(
                            text("SELECT pg_advisory_lock(:key)"), {"key": identity.advisory_key}
                        )
                    async with connection.begin():
                        query = await connection.execute(lookup, parameters)
                        stored = query.mappings().one_or_none()
                        if stored is not None:
                            identity.verify_stored(stored["version"], stored["source"])

                    if stored is None:
                        # Retain the lock connection, but no transaction, during external work.
                        transforming = True
                        try:
                            result = await transformer(source)
                        except TimeoutError:
                            raise
                        except Exception as exc:
                            raise TransformationFailed("Transformation failed") from exc

                        transforming = False
                        async with connection.begin():
                            await connection.execute(
                                text(
                                    "INSERT INTO transformations "
                                    "(version, source_digest, source, result) "
                                    "VALUES (:version, :digest, :source, :result) "
                                    "ON CONFLICT (version, source_digest) DO NOTHING"
                                ),
                                {**parameters, "source": source, "result": result},
                            )
                            # A fresh statement sees a conflicting insert's authoritative row.
                            query = await connection.execute(lookup, parameters)
                            stored = query.mappings().one()
                            identity.verify_stored(stored["version"], stored["source"])

                    # Persistence committed before unlock; rollback-on-return cannot unlock.
                    async with connection.begin():
                        released = await connection.scalar(
                            text("SELECT pg_advisory_unlock(:key)"),
                            {"key": identity.advisory_key},
                        )
                        if released is not True:
                            raise RuntimeError("Transformation lock ownership lost")
                except BaseException:
                    # Even acquisition can fail after the server took ownership. Never pool
                    # a session whose lock state is uncertain. B11 adds protected budgets.
                    await connection.invalidate()
                    raise
            results[source] = stored["result"]
        except TimeoutError as exc:
            # Transformer timeout must retain its existing HTTP 504 classification.
            if transforming:
                raise
            raise DatabaseUnavailable("Database unavailable") from exc
    return results
