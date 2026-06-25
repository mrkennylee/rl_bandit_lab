"""Phase 3 — gridworld MDP API: create + Bellman sweeps to convergence."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


async def test_create_gridworld_defaults_to_russell_norvig(client):
    resp = await client.post("/runs/gridworld", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "gridworld"
    assert body["rows"] == 3 and body["cols"] == 4
    assert body["terminals"] == {"0,3": 1.0, "1,3": -1.0}
    assert body["walls"] == ["1,1"]


async def test_sweeps_converge_to_known_policy(client):
    run_id = (await client.post("/runs/gridworld", json={})).json()["run_id"]
    deltas = []
    result = None
    for _ in range(80):
        result = (await client.post(f"/runs/{run_id}/sweep")).json()
        deltas.append(result["max_delta"])
        if result["converged"]:
            break
    assert result["converged"]
    assert result["sweep_no"] > 1
    assert result["formula"]["key"] == "bellman.optimality"
    # canonical optimal policy spot-checks
    assert result["policy"]["0,0"] == "R"
    assert result["policy"]["1,2"] == "U"
    assert result["policy"]["2,3"] == "L"
    # value iteration drives the Bellman residual down
    assert deltas[-1] < deltas[0]


async def test_sweep_unknown_run_404(client):
    resp = await client.post("/runs/123/sweep")
    assert resp.status_code == 404
