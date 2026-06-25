"""Phase 6 — presence tracking + close-the-website shutdown logic (no DB).

The /presence endpoint is a thin SSE wrapper around client_connected /
client_disconnected; the real end-to-end close-the-tab behaviour is exercised by
the Playwright e2e. Here we test the (deterministic) lifecycle logic directly —
streaming an infinite SSE over httpx in-process is prone to deadlock, so we don't.
"""

from __future__ import annotations

import asyncio
import types

from rl_bandit_lab.web import lifecycle


def _fake_app() -> types.SimpleNamespace:
    app = types.SimpleNamespace(state=types.SimpleNamespace())
    lifecycle.init_presence_state(app)
    return app


def test_client_counting() -> None:
    app = _fake_app()
    app.state.shutdown_enabled = False
    lifecycle.client_connected(app)
    lifecycle.client_connected(app)
    assert app.state.active_clients == 2
    lifecycle.client_disconnected(app)
    assert app.state.active_clients == 1
    lifecycle.client_disconnected(app)
    assert app.state.active_clients == 0


async def test_last_disconnect_triggers_shutdown_after_grace() -> None:
    app = _fake_app()
    app.state.shutdown_enabled = True
    app.state.shutdown_grace = 0.0  # fire immediately
    fired: list[bool] = []
    app.state.shutdown_hook = lambda: fired.append(True)

    lifecycle.client_connected(app)
    lifecycle.client_disconnected(app)
    await asyncio.sleep(0.05)
    assert fired == [True]


async def test_reconnect_within_grace_cancels_shutdown() -> None:
    app = _fake_app()
    app.state.shutdown_enabled = True
    app.state.shutdown_grace = 0.2
    fired: list[bool] = []
    app.state.shutdown_hook = lambda: fired.append(True)

    lifecycle.client_connected(app)
    lifecycle.client_disconnected(app)  # schedules shutdown
    lifecycle.client_connected(app)     # someone navigated back in -> cancel
    await asyncio.sleep(0.3)
    assert fired == []  # shutdown was cancelled


def test_shutdown_not_armed_until_first_client() -> None:
    # disconnect spuriously with no prior client must not schedule a shutdown
    app = _fake_app()
    app.state.shutdown_enabled = True
    lifecycle.client_disconnected(app)
    assert app.state.shutdown_task is None
