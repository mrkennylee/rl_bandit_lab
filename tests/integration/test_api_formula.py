"""Phase 3 — formula derivation retrieval (seeds -> DB -> API)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


async def test_get_formula_returns_ordered_steps(client):
    body = (await client.get("/formula/bandit.ucb")).json()
    assert body["title"]
    step_numbers = [s["step_no"] for s in body["steps"]]
    assert step_numbers == sorted(step_numbers)
    assert len(step_numbers) >= 1


async def test_bellman_formula_keeps_optimality_star(client):
    resp = await client.get("/formula/bellman.optimality")
    assert resp.status_code == 200
    assert "V^*" in resp.json()["latex"]


async def test_unknown_formula_404(client):
    resp = await client.get("/formula/does.not.exist")
    assert resp.status_code == 404
