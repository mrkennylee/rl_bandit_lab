"""Phase 5 — gridworld page, bridge page, navigation, static asset."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


async def test_gridworld_page_renders(client):
    resp = await client.get("/gridworld")
    assert resp.status_code == 200
    assert 'id="grid"' in resp.text
    assert "/static/app_gridworld.js" in resp.text


async def test_bridge_page_renders(client):
    resp = await client.get("/bridge")
    assert resp.status_code == 200
    assert "one-state MDP" in resp.text
    assert "bridge.bandit_is_mdp" in resp.text


async def test_gridworld_js_served(client):
    resp = await client.get("/static/app_gridworld.js")
    assert resp.status_code == 200
    assert "/sweep" in resp.text


async def test_nav_links_present_on_landing(client):
    resp = await client.get("/")
    assert "/gridworld" in resp.text
    assert "/bridge" in resp.text
