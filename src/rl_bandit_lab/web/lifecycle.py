"""Presence tracking: every open page holds an SSE connection (/presence). When
the last one closes, the server shuts itself down — and the local database with
it (resolution #7, updated) — after a short grace so page navigation is ignored.
"""

from __future__ import annotations

import asyncio
import os
import signal

from fastapi import FastAPI

from rl_bandit_lab.config import get_settings
from rl_bandit_lab.logging.system_logger import get_system_logger


def _default_shutdown_hook() -> None:
    get_system_logger().info("last client gone -> self SIGTERM (stops app + local db)")
    os.kill(os.getpid(), signal.SIGTERM)


def init_presence_state(app: FastAPI) -> None:
    settings = get_settings()
    app.state.active_clients = 0
    app.state.had_client = False
    app.state.shutdown_task = None
    app.state.shutdown_enabled = settings.shutdown_on_last_disconnect
    app.state.shutdown_grace = settings.shutdown_grace_seconds
    app.state.shutdown_hook = _default_shutdown_hook


def client_connected(app: FastAPI) -> None:
    if app.state.shutdown_task is not None:
        app.state.shutdown_task.cancel()  # someone arrived (e.g. navigated) — cancel pending shutdown
        app.state.shutdown_task = None
    app.state.active_clients += 1
    app.state.had_client = True


def client_disconnected(app: FastAPI) -> None:
    app.state.active_clients = max(0, app.state.active_clients - 1)
    if (
        app.state.active_clients == 0
        and app.state.had_client
        and app.state.shutdown_enabled
    ):
        app.state.shutdown_task = asyncio.create_task(_grace_then_shutdown(app))


async def _grace_then_shutdown(app: FastAPI) -> None:
    try:
        await asyncio.sleep(app.state.shutdown_grace)
    except asyncio.CancelledError:
        return
    if app.state.active_clients == 0:
        app.state.shutdown_hook()
