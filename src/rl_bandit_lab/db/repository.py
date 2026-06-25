"""Query layer. Functions flush (not commit) so the caller controls the
transaction boundary — the SSE handler commits once per step then releases
the connection. latest_snapshot() powers O(1) agent reconstruction.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rl_bandit_lab.db.models import (
    ArmTruth,
    DerivationStep,
    Formula,
    MdpIteration,
    Pull,
    SimRun,
)


# --- derivations (seed content) --------------------------------------------

async def get_formula(session: AsyncSession, key: str) -> Formula | None:
    result = await session.execute(select(Formula).where(Formula.key == key))
    return result.scalar_one_or_none()


async def get_derivation(session: AsyncSession, key: str) -> list[DerivationStep]:
    result = await session.execute(
        select(DerivationStep)
        .join(Formula)
        .where(Formula.key == key)
        .order_by(DerivationStep.step_no)
    )
    return list(result.scalars().all())


# --- runs -------------------------------------------------------------------

async def create_run(
    session: AsyncSession,
    *,
    mode: str,
    algorithm: str,
    params: dict | None = None,
    n_arms: int | None = None,
) -> SimRun:
    run = SimRun(mode=mode, algorithm=algorithm, params=params or {}, n_arms=n_arms)
    session.add(run)
    await session.flush()
    return run


async def add_arm_truths(
    session: AsyncSession, run_id: int, true_means: Sequence[float]
) -> list[ArmTruth]:
    objs = [
        ArmTruth(run_id=run_id, arm_index=i, true_mean=p)
        for i, p in enumerate(true_means)
    ]
    session.add_all(objs)
    await session.flush()
    return objs


# --- bandit pulls -----------------------------------------------------------

async def record_pull(
    session: AsyncSession,
    *,
    run_id: int,
    step_no: int,
    arm_chosen: int,
    reward: int,
    q_estimate: float,
    n_selected: int,
    reason_code: str,
    explain: dict,
    state_snapshot: dict,
) -> Pull:
    pull = Pull(
        run_id=run_id,
        step_no=step_no,
        arm_chosen=arm_chosen,
        reward=reward,
        q_estimate=q_estimate,
        n_selected=n_selected,
        reason_code=reason_code,
        explain=explain,
        state_snapshot=state_snapshot,
    )
    session.add(pull)
    await session.flush()
    return pull


async def latest_snapshot(session: AsyncSession, run_id: int) -> dict | None:
    """The most recent pull's state_snapshot — used to rebuild the agent."""
    result = await session.execute(
        select(Pull.state_snapshot)
        .where(Pull.run_id == run_id)
        .order_by(desc(Pull.step_no))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_run_history(session: AsyncSession, run_id: int) -> list[Pull]:
    result = await session.execute(
        select(Pull).where(Pull.run_id == run_id).order_by(Pull.step_no)
    )
    return list(result.scalars().all())


# --- gridworld sweeps -------------------------------------------------------

async def record_iteration(
    session: AsyncSession,
    *,
    run_id: int,
    sweep_no: int,
    max_delta: float,
    values: dict,
    policy: dict,
) -> MdpIteration:
    iteration = MdpIteration(
        run_id=run_id,
        sweep_no=sweep_no,
        max_delta=max_delta,
        values=values,
        policy=policy,
    )
    session.add(iteration)
    await session.flush()
    return iteration


async def last_iteration(session: AsyncSession, run_id: int) -> MdpIteration | None:
    result = await session.execute(
        select(MdpIteration)
        .where(MdpIteration.run_id == run_id)
        .order_by(desc(MdpIteration.sweep_no))
        .limit(1)
    )
    return result.scalar_one_or_none()


# --- helpers ----------------------------------------------------------------

async def get_run(session: AsyncSession, run_id: int) -> SimRun | None:
    return await session.get(SimRun, run_id)


async def max_step(session: AsyncSession, run_id: int) -> int:
    result = await session.execute(
        select(func.max(Pull.step_no)).where(Pull.run_id == run_id)
    )
    return result.scalar() or 0


async def get_arm_truths(session: AsyncSession, run_id: int) -> list[float]:
    result = await session.execute(
        select(ArmTruth.true_mean)
        .where(ArmTruth.run_id == run_id)
        .order_by(ArmTruth.arm_index)
    )
    return [float(x) for x in result.scalars().all()]
