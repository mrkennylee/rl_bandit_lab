"""Presence channel — an SSE connection held open while a page is visible. Its
connect/disconnect drives the "shut everything down when the website is closed"
behaviour in lifecycle.py."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from rl_bandit_lab.web import lifecycle

router = APIRouter(tags=["presence"])


@router.get("/presence")
async def presence(request: Request):
    app = request.app

    async def event_gen():
        lifecycle.client_connected(app)
        try:
            while not await request.is_disconnected():
                yield {"event": "ping", "data": "alive"}
                await asyncio.sleep(15)
        finally:
            lifecycle.client_disconnected(app)

    return EventSourceResponse(event_gen())
