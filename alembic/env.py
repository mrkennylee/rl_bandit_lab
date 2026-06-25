"""Alembic environment — migrations run synchronously (psycopg3 sync) even though
the app uses an async engine at runtime. URL + metadata come from the project.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rl_bandit_lab.config import get_settings  # noqa: E402
from rl_bandit_lab.db.models import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    # disable_existing_loggers=False: running migrations from inside the app (on
    # startup) must NOT silence the app's own "rl_bandit_lab" system logger.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
