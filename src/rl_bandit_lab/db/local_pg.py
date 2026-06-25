"""Project-local PostgreSQL lifecycle (decision #7: DB data lives in the project's
default storage dir, ./.pgdata, and persists on disk). Closing the app stops the
compute; these files remain.

CLI:  python -m rl_bandit_lab.db.local_pg {bootstrap|init|start|stop|status|ensure-db}
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import psycopg

from rl_bandit_lab.config import get_settings
from rl_bandit_lab.logging.system_logger import get_system_logger

_BIN_CANDIDATES = [
    "/opt/homebrew/opt/postgresql@16/bin",
    "/usr/local/opt/postgresql@16/bin",
    "/opt/homebrew/bin",
    "/usr/local/bin",
]
_SOCKET_DIR = "/tmp"  # short path: avoids the macOS unix-socket length limit


def postgres_bin_dir() -> str | None:
    found = shutil.which("pg_ctl")
    if found:
        return str(Path(found).parent)
    for cand in _BIN_CANDIDATES:
        if (Path(cand) / "pg_ctl").exists():
            return cand
    return None


def _bin(name: str) -> str:
    bin_dir = postgres_bin_dir()
    if bin_dir is None:
        raise RuntimeError("PostgreSQL binaries not found (try: brew install postgresql@16)")
    return str(Path(bin_dir) / name)


def is_initialized(pgdata: Path) -> bool:
    return (pgdata / "PG_VERSION").exists()


def status(pgdata: Path | None = None) -> bool:
    pgdata = pgdata or get_settings().pgdata_dir
    result = subprocess.run(
        [_bin("pg_ctl"), "-D", str(pgdata), "status"], capture_output=True
    )
    return result.returncode == 0


def init(pgdata: Path | None = None) -> None:
    log = get_system_logger()
    pgdata = pgdata or get_settings().pgdata_dir
    if is_initialized(pgdata):
        log.info("local pg already initialised at %s", pgdata)
        return
    pgdata.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            _bin("initdb"), "-D", str(pgdata),
            "--auth-local=trust", "--auth-host=trust", "--encoding=UTF8",
        ],
        check=True,
    )
    log.info("initdb complete at %s", pgdata)


def start(pgdata: Path | None = None, port: int | None = None) -> bool:
    """Start the local cluster. Returns True if this call started it, False if it
    was already running (so the caller knows whether it's responsible for it)."""
    log = get_system_logger()
    settings = get_settings()
    pgdata = pgdata or settings.pgdata_dir
    port = port or settings.pg_port
    if status(pgdata):
        log.info("local pg already running")
        return False
    logfile = pgdata / "server.log"
    subprocess.run(
        [
            _bin("pg_ctl"), "-D", str(pgdata), "-l", str(logfile),
            "-o", f"-p {port} -k {_SOCKET_DIR}", "start", "-w",
        ],
        check=True,
    )
    log.info("local pg started on 127.0.0.1:%s", port)
    return True


def stop(pgdata: Path | None = None) -> None:
    log = get_system_logger()
    pgdata = pgdata or get_settings().pgdata_dir
    if not status(pgdata):
        log.info("local pg not running")
        return
    subprocess.run([_bin("pg_ctl"), "-D", str(pgdata), "-m", "fast", "stop", "-w"], check=True)
    log.info("local pg stopped")


def ensure_database(port: int | None = None, dbname: str = "rl_bandit_lab") -> None:
    log = get_system_logger()
    port = port or get_settings().pg_port
    with psycopg.connect(
        host="127.0.0.1", port=port, dbname="postgres", autocommit=True
    ) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        ).fetchone()
        if exists:
            log.info("database %s already exists", dbname)
        else:
            conn.execute(f'CREATE DATABASE "{dbname}"')
            log.info("created database %s", dbname)


def bootstrap() -> bool:
    """Init + start + create database. Returns True if this call started pg."""
    init()
    started = start()
    ensure_database()
    return started


def _main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "bootstrap"
    actions = {
        "init": init,
        "start": start,
        "stop": stop,
        "status": lambda: print("running" if status() else "stopped"),
        "ensure-db": ensure_database,
        "bootstrap": bootstrap,
    }
    if cmd not in actions:
        raise SystemExit(f"usage: local_pg {{{'|'.join(actions)}}}")
    actions[cmd]()


if __name__ == "__main__":
    _main(sys.argv)
