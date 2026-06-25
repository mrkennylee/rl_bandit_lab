"""Central settings. One source of truth for paths, DB url, and run timestamp.

PROJECT_ROOT resolves from this file's location so logs / .pgdata land in the
project's default storage directory regardless of the current working dir.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/rl_bandit_lab/config.py -> parents[2] == project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "rl_bandit_lab"
    serve_host: str = "127.0.0.1"
    serve_port: int = 8080
    database_url: str = "postgresql+psycopg://localhost:5433/rl_bandit_lab"
    pg_port: int = 5433  # project-local postgres listens here (avoids clashing with 5432)
    log_dir: Path = PROJECT_ROOT / "logs"
    pgdata_dir: Path = PROJECT_ROOT / ".pgdata"
    autoplay_default_interval: float = 0.5  # seconds between auto-play steps
    # When the last browser tab closes, stop the app AND the local database so no
    # process is left running on the user's machine (data files in .pgdata remain).
    shutdown_on_last_disconnect: bool = True
    shutdown_grace_seconds: float = 4.0  # grace so page navigation doesn't shut down
    manage_local_db: bool = True  # app owns the local pg lifecycle (start on boot, stop on close)
    # Stamped once per process (lru_cache below) -> shared by all log files this run.
    run_timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    @property
    def system_log_dir(self) -> Path:
        return self.log_dir / "system"

    @property
    def mdc_log_dir(self) -> Path:
        return self.log_dir / "mdc"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.system_log_dir.mkdir(parents=True, exist_ok=True)
    s.mdc_log_dir.mkdir(parents=True, exist_ok=True)
    return s
