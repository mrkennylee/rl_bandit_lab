"""Phase 3 — bandit API + SSE auto-play."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.integration


async def _new_run(client, **kw) -> int:
    body = {"n_arms": 3, "algorithm": "ucb1", "seed": 1, **kw}
    resp = await client.post("/runs/bandit", json=body)
    assert resp.status_code == 200
    return resp.json()["run_id"]


async def test_create_bandit_run(client):
    resp = await client.post("/runs/bandit", json={"n_arms": 3, "algorithm": "ucb1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_arms"] == 3
    assert body["n_truths"] == 3
    assert isinstance(body["run_id"], int)


async def test_step_persists_and_returns_formula(client):
    run_id = await _new_run(client)
    first = (await client.post(f"/runs/{run_id}/step")).json()
    assert first["step_no"] == 1
    assert first["reward"] in (0, 1)
    assert first["reason_code"] in ("explore", "exploit")
    assert first["formula"]["key"] == "bandit.ucb"
    assert len(first["formula"]["steps"]) >= 1
    second = (await client.post(f"/runs/{run_id}/step")).json()
    assert second["step_no"] == 2


async def test_step_reconstructs_state_from_db(client):
    # No in-memory agent survives between requests; total pulls == steps proves
    # the agent is faithfully rebuilt from the DB snapshot each step.
    run_id = await _new_run(client, seed=2)
    last = None
    for _ in range(7):
        last = (await client.post(f"/runs/{run_id}/step")).json()
    assert last["step_no"] == 7
    assert sum(last["counts"]) == 7


async def test_invalid_algorithm_rejected(client):
    resp = await client.post("/runs/bandit", json={"n_arms": 3, "algorithm": "nope"})
    assert resp.status_code == 422


async def test_step_unknown_run_404(client):
    resp = await client.post("/runs/999/step")
    assert resp.status_code == 404


async def test_stream_emits_increasing_steps(client):
    run_id = await _new_run(client, n_arms=2, seed=3)
    steps: list[int] = []
    async with client.stream(
        "GET", f"/runs/{run_id}/stream?interval=0.01&max_steps=3"
    ) as resp:
        assert resp.status_code == 200
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                payload = json.loads(line[len("data:"):].strip())
                if "step_no" in payload:
                    steps.append(payload["step_no"])
            if len(steps) >= 3:
                break
    assert steps == [1, 2, 3]
