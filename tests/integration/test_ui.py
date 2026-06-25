"""Phase 4 — server-rendered pages and static assets."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


async def test_index_renders_setup_form(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert 'id="setup-form"' in resp.text
    assert "slot machines" in resp.text.lower()


async def test_lab_renders_one_machine_per_arm(client):
    run_id = (await client.post("/runs/bandit", json={"n_arms": 4, "algorithm": "ucb1"})).json()["run_id"]
    resp = await client.get(f"/lab/{run_id}")
    assert resp.status_code == 200
    assert resp.text.count('class="machine"') == 4
    assert f'data-run-id="{run_id}"' in resp.text
    assert "/static/app.js" in resp.text


async def test_lab_unknown_run_404(client):
    resp = await client.get("/lab/99999")
    assert resp.status_code == 404


async def test_static_css_served(client):
    resp = await client.get("/static/app.css")
    assert resp.status_code == 200
    assert ".machine" in resp.text


async def test_static_js_served(client):
    resp = await client.get("/static/app.js")
    assert resp.status_code == 200
    assert "EventSource" in resp.text
