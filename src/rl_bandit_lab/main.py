"""Entry point: `python -m rl_bandit_lab.main` (or via uvicorn directly)."""

from __future__ import annotations

import uvicorn

from rl_bandit_lab.config import get_settings


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "rl_bandit_lab.web.app:app",
        host=settings.serve_host,
        port=settings.serve_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
