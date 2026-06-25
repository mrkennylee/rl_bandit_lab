"""Integration harness: an ephemeral PostgreSQL (Docker-free) via pytest-postgresql
pointed at the local brew binaries. Exposes:
  * db_session — a bare async session (repository tests)
  * client     — an httpx AsyncClient driving the ASGI app, sharing the test loop
                 and pointed at the ephemeral DB (with formulas seeded)
Skips cleanly when no postgres binary is present.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio

from rl_bandit_lab.db.local_pg import postgres_bin_dir
from rl_bandit_lab.db.models import Base

_BIN = postgres_bin_dir()
if _BIN:
    os.environ["PATH"] = _BIN + os.pathsep + os.environ.get("PATH", "")

POSTGRES_AVAILABLE = _BIN is not None and os.path.exists(os.path.join(_BIN, "pg_ctl"))


if POSTGRES_AVAILABLE:
    import httpx
    from pytest_postgresql import factories
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from rl_bandit_lab.db.seed import load_seed_data, seed_formulas
    from rl_bandit_lab.web.app import create_app

    postgresql_proc = factories.postgresql_proc(
        executable=os.path.join(_BIN, "pg_ctl"),
        unixsocketdir="/tmp",
    )

    def _url(info) -> str:
        return f"postgresql+psycopg://{info.user}@{info.host}:{info.port}/{info.dbname}"

    @pytest_asyncio.fixture
    async def db_session(postgresql):
        engine = create_async_engine(_url(postgresql.info), poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            yield session
        await engine.dispose()

    @pytest_asyncio.fixture
    async def client(postgresql):
        engine = create_async_engine(_url(postgresql.info), poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:  # seed formulas so /step + /formula work
            await seed_formulas(session, load_seed_data())
            await session.commit()

        app = create_app()
        app.state.engine = engine
        app.state.sessionmaker = maker  # guard in lifespan leaves this untouched
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
        await engine.dispose()

else:  # pragma: no cover - environment without postgres

    @pytest_asyncio.fixture
    async def db_session():
        pytest.skip("PostgreSQL binaries not found; skipping integration tests")
        yield None

    @pytest_asyncio.fixture
    async def client():
        pytest.skip("PostgreSQL binaries not found; skipping integration tests")
        yield None
