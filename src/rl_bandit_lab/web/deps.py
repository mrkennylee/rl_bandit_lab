"""Request-scoped async session. The sessionmaker lives on app.state so tests
can point it at an ephemeral database. SSE does NOT use this — it opens a fresh
session per step (and releases it during the sleep) to keep the pool free.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session
