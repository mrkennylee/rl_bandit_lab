"""Phase 2 integration tests — repository against a real ephemeral PostgreSQL.

Covers run/arm-truth/pull/iteration persistence, the latest_snapshot
reconstruction contract, ordered derivation retrieval, and the Bernoulli /
probability CHECK constraints.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from rl_bandit_lab.db import repository as repo
from rl_bandit_lab.db.models import ArmTruth, DerivationStep, Formula

pytestmark = pytest.mark.integration


async def test_create_run_and_arm_truths(db_session):
    run = await repo.create_run(
        db_session, mode="bandit", algorithm="ucb1", params={"c": 2.0}, n_arms=3
    )
    assert run.id is not None
    await repo.add_arm_truths(db_session, run.id, [0.2, 0.5, 0.8])
    await db_session.commit()

    rows = (
        await db_session.execute(
            select(ArmTruth).where(ArmTruth.run_id == run.id).order_by(ArmTruth.arm_index)
        )
    ).scalars().all()
    assert [r.true_mean for r in rows] == pytest.approx([0.2, 0.5, 0.8])


async def test_record_pull_and_latest_snapshot(db_session):
    run = await repo.create_run(
        db_session, mode="bandit", algorithm="ucb1", n_arms=2, params={}
    )
    await repo.record_pull(
        db_session, run_id=run.id, step_no=1, arm_chosen=0, reward=1,
        q_estimate=1.0, n_selected=1, reason_code="explore",
        explain={"text": "first"}, state_snapshot={"counts": [1, 0], "values": [1.0, 0.0]},
    )
    await repo.record_pull(
        db_session, run_id=run.id, step_no=2, arm_chosen=1, reward=0,
        q_estimate=0.0, n_selected=1, reason_code="explore",
        explain={"text": "second"}, state_snapshot={"counts": [1, 1], "values": [1.0, 0.0]},
    )
    snap = await repo.latest_snapshot(db_session, run.id)
    assert snap == {"counts": [1, 1], "values": [1.0, 0.0]}

    history = await repo.get_run_history(db_session, run.id)
    assert [p.step_no for p in history] == [1, 2]


async def test_latest_snapshot_is_none_without_pulls(db_session):
    run = await repo.create_run(
        db_session, mode="bandit", algorithm="ucb1", n_arms=2, params={}
    )
    assert await repo.latest_snapshot(db_session, run.id) is None


async def test_reward_must_be_bernoulli(db_session):
    run = await repo.create_run(
        db_session, mode="bandit", algorithm="ucb1", n_arms=2, params={}
    )
    with pytest.raises(IntegrityError):
        await repo.record_pull(
            db_session, run_id=run.id, step_no=1, arm_chosen=0, reward=2,
            q_estimate=0.0, n_selected=1, reason_code="x",
            explain={}, state_snapshot={},
        )


async def test_true_mean_must_be_probability(db_session):
    run = await repo.create_run(
        db_session, mode="bandit", algorithm="ucb1", n_arms=1, params={}
    )
    with pytest.raises(IntegrityError):
        await repo.add_arm_truths(db_session, run.id, [1.5])


async def test_derivation_returned_in_step_order(db_session):
    formula = Formula(key="bandit.ucb", title="UCB1", latex="a_t = ...", plain_explain="b")
    formula.steps = [
        DerivationStep(step_no=2, latex="line2", note="n2"),
        DerivationStep(step_no=1, latex="line1", note="n1"),
    ]
    db_session.add(formula)
    await db_session.commit()

    steps = await repo.get_derivation(db_session, "bandit.ucb")
    assert [s.step_no for s in steps] == [1, 2]
    fetched = await repo.get_formula(db_session, "bandit.ucb")
    assert fetched is not None and fetched.title == "UCB1"


async def test_record_iteration(db_session):
    run = await repo.create_run(
        db_session, mode="gridworld", algorithm="value_iteration", params={"gamma": 1.0}
    )
    iteration = await repo.record_iteration(
        db_session, run_id=run.id, sweep_no=1, max_delta=0.5,
        values={"0,0": 0.1}, policy={"0,0": "R"},
    )
    await db_session.commit()
    assert iteration.id is not None
