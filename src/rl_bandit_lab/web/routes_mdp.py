"""Gridworld MDP endpoints: create a run (defaults to Russell-Norvig 4x3) and
advance one Bellman value-iteration sweep at a time.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from rl_bandit_lab import services
from rl_bandit_lab.rl.gridworld import GridworldMDP
from rl_bandit_lab.web.deps import get_session
from rl_bandit_lab.web.schemas import GridworldRunIn

router = APIRouter(prefix="/runs", tags=["gridworld"])


def _params_from_body(body: GridworldRunIn) -> dict:
    if body.rows is None or body.cols is None or not body.terminals:
        return services.gridworld_params_from_mdp(
            GridworldMDP.russell_norvig(), theta=body.theta
        )
    return {
        "rows": body.rows,
        "cols": body.cols,
        "terminals": body.terminals,
        "walls": body.walls or [],
        "living_reward": body.living_reward,
        "gamma": body.gamma,
        "noise": body.noise,
        "theta": body.theta,
    }


@router.post("/gridworld")
async def create_gridworld(
    body: GridworldRunIn = GridworldRunIn(),
    session: AsyncSession = Depends(get_session),
):
    params = _params_from_body(body)
    run = await services.create_gridworld_run(session, params=params)
    await session.commit()
    return {
        "run_id": run.id,
        "mode": "gridworld",
        "rows": params["rows"],
        "cols": params["cols"],
        "terminals": params["terminals"],
        "walls": params["walls"],
    }


@router.post("/{run_id}/sweep")
async def sweep(run_id: int, session: AsyncSession = Depends(get_session)):
    if await services.get_run(session, run_id, mode="gridworld") is None:
        raise HTTPException(status_code=404, detail=f"no gridworld run {run_id}")
    result = await services.gridworld_sweep(session, run_id)
    await session.commit()
    return result
