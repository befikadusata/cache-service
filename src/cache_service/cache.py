"""Versioned successful-result caching with short PostgreSQL transactions."""

import asyncio
from collections.abc import Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncEngine

from cache_service.coordination import DatabaseUnavailable, TransformationTimedOut
from cache_service.identity import transformation_identity
from cache_service.transformation import Transformer

_READ_BATCH_SIZE = 500


class TransformationFailed(RuntimeError):
    """The replaceable transformer failed before publication."""


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

    coordination = engine.get_execution_options()["cache_coordination"]
    settings = coordination.settings
    for source, identity in identities.items():
        if source in results:
            continue
        parameters = {"version": version, "digest": identity.source_digest}
        lookup = text(
            "SELECT version, source, result FROM transformations "
            "WHERE version = :version AND source_digest = :digest"
        )
        async with coordination.connection(engine, identity.advisory_key) as connection:
            # Transaction-local budgets must not leak into the pooled session.
            async with connection.begin():
                lock_ms = max(1, int(settings.advisory_lock_timeout_seconds * 1000))
                await connection.execute(
                    text("SELECT set_config('lock_timeout', :lock, true), "
                         "set_config('statement_timeout', :statement, true)"),
                    {"lock": str(lock_ms), "statement": str(lock_ms + 1000)},
                )
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
                try:
                    async with asyncio.timeout(settings.transformation_timeout_seconds):
                        result = await transformer(source)
                except TimeoutError as exc:
                    raise TransformationTimedOut("Transformation timed out") from exc
                except Exception as exc:
                    raise TransformationFailed("Transformation failed") from exc

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
        results[source] = stored["result"]
    return results
