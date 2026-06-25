"""FastAPI app factory.

Self-contained lifecycle (resolution #7, updated): when the app owns the local
database (the normal teaching setup), startup boots the project-local Postgres,
applies migrations, and seeds formulas; shutdown disposes the engine and STOPS
the database. Closing the last browser tab (see lifecycle.py / routes_presence)
triggers that shutdown, so nothing is left running — only files on disk remain.

Tests pre-set app.state.sessionmaker (ephemeral DB) and never run lifespan, so
none of the local-db management touches them.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from rl_bandit_lab import __version__
from rl_bandit_lab.config import PROJECT_ROOT, get_settings
from rl_bandit_lab.db import local_pg
from rl_bandit_lab.db.session import get_engine, get_sessionmaker
from rl_bandit_lab.logging.system_logger import get_system_logger
from rl_bandit_lab.web.netcheck import ensure_port_available
from rl_bandit_lab.web import (
    lifecycle,
    routes_bandit,
    routes_formula,
    routes_mdp,
    routes_presence,
    routes_ui,
)


def _alembic_upgrade() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")


async def _bootstrap_local_db(app: FastAPI) -> bool:
    from rl_bandit_lab.db import repository as repo
    from rl_bandit_lab.db.seed import load_seed_data, seed_formulas

    started = local_pg.bootstrap()             # init + start + create database
    await asyncio.to_thread(_alembic_upgrade)  # ensure schema (idempotent)
    async with app.state.sessionmaker() as session:  # seed formulas if absent
        if await repo.get_formula(session, "bellman.optimality") is None:
            await seed_formulas(session, load_seed_data())
            await session.commit()
    return started


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = get_system_logger()
    settings = get_settings()
    app.state.started_pg = False
    if not hasattr(app.state, "sessionmaker"):
        if settings.manage_local_db:
            # Fail fast BEFORE touching the database: a second launch on a busy
            # port must not bootstrap (then tear down) the running instance's pg.
            ensure_port_available(settings.serve_host, settings.serve_port)
        app.state.engine = get_engine()
        app.state.sessionmaker = get_sessionmaker()
        app.state.owns_engine = True
        if settings.manage_local_db:
            app.state.started_pg = await _bootstrap_local_db(app)
    else:
        app.state.owns_engine = False

    log.info("rl_bandit_lab starting")
    yield
    log.info("rl_bandit_lab shutting down")
    if getattr(app.state, "owns_engine", False):
        await app.state.engine.dispose()
        # only stop pg if THIS process started it (don't kill another instance's db)
        if settings.manage_local_db and app.state.started_pg:
            local_pg.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    lifecycle.init_presence_state(app)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(routes_ui.router)
    app.include_router(routes_presence.router)
    app.include_router(routes_bandit.router)
    app.include_router(routes_mdp.router)
    app.include_router(routes_formula.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "version": __version__}

    return app


app = create_app()
