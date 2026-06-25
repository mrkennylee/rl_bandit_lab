"""Bandit endpoints: create a run, single manual step, and the SSE auto-play
stream. The stream is the resolution #1 / #7 design — session-per-step,
connection released during the sleep, and the loop ends on client disconnect.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from rl_bandit_lab import services
from rl_bandit_lab.config import get_settings
from rl_bandit_lab.logging.mdc_logger import MdcLogger
from rl_bandit_lab.web.deps import get_session
from rl_bandit_lab.web.schemas import BanditRunIn

router = APIRouter(prefix="/runs", tags=["bandit"])


@router.post("/bandit")
async def create_bandit(body: BanditRunIn, session: AsyncSession = Depends(get_session)):
    run, true_means = await services.create_bandit_run(
        session,
        n_arms=body.n_arms,
        algorithm=body.algorithm,
        params={"epsilon": body.epsilon, "c": body.c},
        seed=body.seed,
        true_means=body.true_means,
    )
    await session.commit()
    return {
        "run_id": run.id,
        "n_arms": body.n_arms,
        "algorithm": body.algorithm,
        "n_truths": len(true_means),
    }


@router.post("/{run_id}/step")
async def step(run_id: int, session: AsyncSession = Depends(get_session)):
    if await services.get_run(session, run_id, mode="bandit") is None:
        raise HTTPException(status_code=404, detail=f"no bandit run {run_id}")
    result = await services.bandit_step(session, run_id)
    await session.commit()
    return result


@router.get("/{run_id}/stream")
async def stream(
    run_id: int,
    request: Request,
    interval: float | None = None,
    max_steps: int = 500,
):
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        if await services.get_run(session, run_id, mode="bandit") is None:
            raise HTTPException(status_code=404, detail=f"no bandit run {run_id}")

    step_interval = (
        get_settings().autoplay_default_interval if interval is None else interval
    )

    async def event_gen():
        sent = 0
        mdc = MdcLogger("bandit_stream", run_id=run_id)
        try:
            while sent < max_steps:
                if await request.is_disconnected():
                    break
                async with sessionmaker() as session:  # acquire
                    result = await services.bandit_step(session, run_id)
                    await session.commit()             # release before sleep
                sent += 1
                mdc.line(
                    f"step {result['step_no']} | arm {result['arm_chosen']} | "
                    f"reward {result['reward']} | {result['reason_code']}"
                )
                yield {"event": "step", "data": json.dumps(result)}
                await asyncio.sleep(step_interval)
            yield {"event": "done", "data": json.dumps({"sent": sent})}
        finally:
            mdc.close()

    return EventSourceResponse(event_gen())
