"""Per-process admission and bounded cleanup for session advisory locks."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from asyncpg import Connection
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from cache_service.config import Settings


class DatabaseUnavailable(RuntimeError):
    """Capacity or database ownership could not be established safely."""


class TransformationTimedOut(TimeoutError):
    """External work exceeded its deadline."""


class Coordination:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.slots = asyncio.Semaphore(settings.coordination_slots)

    @asynccontextmanager
    async def connection(self, engine: AsyncEngine, key: int) -> AsyncIterator[AsyncConnection]:
        try:
            async with asyncio.timeout(self.settings.admission_timeout_seconds):
                await self.slots.acquire()
        except TimeoutError as exc:
            raise DatabaseUnavailable("Coordination capacity unavailable") from exc

        connection = None
        failed = True
        driver = None
        try:
            try:
                async with asyncio.timeout(self.settings.pool_timeout_seconds):
                    connection = await engine.connect()
            except TimeoutError as exc:
                raise DatabaseUnavailable("Database unavailable") from exc
            driver = connection.sync_connection.connection.driver_connection
            yield connection
            failed = False
        except TimeoutError as exc:
            if isinstance(exc, TransformationTimedOut):
                raise
            raise DatabaseUnavailable("Database unavailable") from exc
        finally:
            try:
                if connection is not None:
                    await self._protected_cleanup(connection, key, failed, driver)
            finally:
                self.slots.release()

    async def _protected_cleanup(
        self, connection: AsyncConnection, key: int, failed: bool, driver: Connection | None
    ) -> None:
        # Keep a strong task reference and wait through repeated request cancellation.
        task = asyncio.create_task(self._cleanup(connection, key, failed, driver))
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        if cancelled:
            # Retrieve any exception before propagating cancellation to the request.
            task.exception()
            raise asyncio.CancelledError
        task.result()

    async def _cleanup(
        self, connection: AsyncConnection, key: int, failed: bool, driver: Connection | None
    ) -> None:
        # Capture the physical driver before invalidation detaches it. asyncpg's
        # synchronous terminate closes the socket even if graceful cleanup times out.
        budget = self.settings.cleanup_timeout_seconds / 2
        try:
            async with asyncio.timeout(budget):
                if failed:
                    await connection.invalidate()
                else:
                    async with connection.begin():
                        released = await connection.scalar(
                            text("SELECT pg_advisory_unlock(:key)"), {"key": key}
                        )
                        if released is not True:
                            raise DatabaseUnavailable("Transformation lock ownership lost")
                await connection.close()
        except BaseException as exc:
            # Never return uncertain session state to the pool. Force-close has no await.
            if driver is not None:
                driver.terminate()
            try:
                async with asyncio.timeout(budget):
                    await connection.invalidate()
                    await connection.close()
            except Exception as disposal_error:
                raise DatabaseUnavailable("Database cleanup failed") from disposal_error
            raise DatabaseUnavailable("Database cleanup failed") from exc
