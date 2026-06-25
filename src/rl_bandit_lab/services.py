"""Orchestration between the RL engine and the database.

The bandit agent is reconstructed from the latest pull snapshot on every step
(stateless-HTTP safe). Both arm selection and the Bernoulli reward draw use a
per-step deterministic RNG seeded by (run_seed, step_no) so any step is
reproducible from the DB alone.
"""

from __future__ import annotations

import math

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from rl_bandit_lab.db import repository as repo
from rl_bandit_lab.db.models import SimRun
from rl_bandit_lab.rl.bandit import rebuild_agent
from rl_bandit_lab.rl.explain import build_explanation
from rl_bandit_lab.rl.gridworld import GridworldMDP


# --- gridworld <-> JSON-able params ----------------------------------------

def _json_safe(obj):
    """Replace non-finite floats (inf/nan) with None so values are valid JSON
    for both JSONB storage and the browser's JSON.parse."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    return obj


def _skey(state: tuple[int, int]) -> str:
    return f"{state[0]},{state[1]}"


def _sparse(key: str) -> tuple[int, int]:
    r, c = key.split(",")
    return (int(r), int(c))


def gridworld_params_from_mdp(mdp: GridworldMDP, theta: float = 1e-8) -> dict:
    return {
        "rows": mdp.n_rows,
        "cols": mdp.n_cols,
        "terminals": {_skey(s): r for s, r in mdp.terminals.items()},
        "walls": [_skey(s) for s in mdp.walls],
        "living_reward": mdp.living_reward,
        "gamma": mdp.gamma,
        "noise": mdp.noise,
        "theta": theta,
    }


def build_gridworld(params: dict) -> GridworldMDP:
    return GridworldMDP(
        n_rows=params["rows"],
        n_cols=params["cols"],
        terminals={_sparse(k): float(v) for k, v in params["terminals"].items()},
        walls={_sparse(k) for k in params.get("walls", [])},
        living_reward=params.get("living_reward", -0.04),
        gamma=params.get("gamma", 1.0),
        noise=params.get("noise", 0.2),
    )


# --- shared -----------------------------------------------------------------

async def get_run(session: AsyncSession, run_id: int, mode: str | None = None) -> SimRun | None:
    run = await repo.get_run(session, run_id)
    if run is None or (mode is not None and run.mode != mode):
        return None
    return run


async def formula_payload(session: AsyncSession, key: str) -> dict | None:
    formula = await repo.get_formula(session, key)
    if formula is None:
        return None
    steps = await repo.get_derivation(session, key)
    return {
        "key": formula.key,
        "title": formula.title,
        "latex": formula.latex,
        "plain_explain": formula.plain_explain,
        "steps": [{"step_no": s.step_no, "latex": s.latex, "note": s.note} for s in steps],
    }


# --- bandit -----------------------------------------------------------------

async def create_bandit_run(
    session: AsyncSession,
    *,
    n_arms: int,
    algorithm: str,
    params: dict,
    seed: int,
    true_means: list[float] | None = None,
) -> tuple[SimRun, list[float]]:
    run_params = dict(params)
    run_params["rng_seed"] = seed
    run = await repo.create_run(
        session, mode="bandit", algorithm=algorithm, params=run_params, n_arms=n_arms
    )
    if true_means is None:
        rng = np.random.default_rng(seed)
        true_means = [round(float(p), 6) for p in rng.uniform(0.1, 0.9, n_arms)]
    await repo.add_arm_truths(session, run.id, true_means)
    return run, true_means


async def bandit_step(session: AsyncSession, run_id: int) -> dict:
    run = await repo.get_run(session, run_id)
    seed = int(run.params.get("rng_seed", 0))
    snapshot = await repo.latest_snapshot(session, run_id)
    step_no = await repo.max_step(session, run_id) + 1

    agent = rebuild_agent(run.algorithm, run.n_arms, run.params, seed=seed, snapshot=snapshot)
    # deterministic, reconstructable per-step streams for selection and reward
    agent.rng = np.random.default_rng((seed, step_no))
    arm = agent.select()

    truths = await repo.get_arm_truths(session, run_id)
    reward = int(np.random.default_rng((seed, step_no, 7919)).random() < truths[arm])
    agent.update(arm, reward)

    explanation = _json_safe(build_explanation(agent, arm))
    await repo.record_pull(
        session,
        run_id=run_id,
        step_no=step_no,
        arm_chosen=arm,
        reward=reward,
        q_estimate=float(agent.values[arm]),
        n_selected=int(agent.counts[arm]),
        reason_code=explanation["reason_code"],
        explain=explanation,
        state_snapshot=agent.snapshot(),
    )
    formula = await formula_payload(session, explanation["formula_key"])
    return {
        "run_id": run_id,
        "mode": "bandit",
        "step_no": step_no,
        "arm_chosen": arm,
        "reward": reward,
        "reason_code": explanation["reason_code"],
        "scores": explanation["scores"],
        "q_values": agent.values.tolist(),
        "counts": agent.counts.tolist(),
        "n_arms": run.n_arms,
        "explanation": explanation,
        "formula": formula,
    }


# --- gridworld --------------------------------------------------------------

async def create_gridworld_run(session: AsyncSession, *, params: dict) -> SimRun:
    return await repo.create_run(
        session, mode="gridworld", algorithm="value_iteration", params=params
    )


async def gridworld_sweep(session: AsyncSession, run_id: int) -> dict:
    run = await repo.get_run(session, run_id)
    mdp = build_gridworld(run.params)
    theta = float(run.params.get("theta", 1e-8))

    last = await repo.last_iteration(session, run_id)
    if last is None:
        values = {s: 0.0 for s in mdp.states()}
        for s, r in mdp.terminals.items():
            values[s] = r
        sweep_no = 1
    else:
        values = {_sparse(k): float(v) for k, v in last.values.items()}
        sweep_no = last.sweep_no + 1

    new_values, policy, delta = mdp.value_iteration_step(values)
    values_ser = {_skey(s): round(float(v), 8) for s, v in new_values.items()}
    policy_ser = {_skey(s): a for s, a in policy.items() if a is not None}

    await repo.record_iteration(
        session,
        run_id=run_id,
        sweep_no=sweep_no,
        max_delta=float(delta),
        values=values_ser,
        policy=policy_ser,
    )
    return {
        "run_id": run_id,
        "mode": "gridworld",
        "sweep_no": sweep_no,
        "max_delta": float(delta),
        "converged": bool(delta < theta),
        "rows": mdp.n_rows,
        "cols": mdp.n_cols,
        "values": values_ser,
        "policy": policy_ser,
        "terminals": {_skey(s): r for s, r in mdp.terminals.items()},
        "walls": [_skey(s) for s in mdp.walls],
        "formula": await formula_payload(session, "bellman.optimality"),
    }
