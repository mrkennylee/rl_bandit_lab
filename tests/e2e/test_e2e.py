"""Opt-in browser end-to-end test (RUN_E2E=1). Boots a real uvicorn server against
the project-local PostgreSQL, seeds it, and drives the UI with Playwright:
landing -> bandit lab -> two steps, then gridworld -> auto-sweep to convergence.

Skipped by default so the normal suite needs no browser/server. Enable with:
    RUN_E2E=1 pytest -m e2e
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
import urllib.request

import pytest

from rl_bandit_lab.config import PROJECT_ROOT

RUN = os.environ.get("RUN_E2E") == "1"
try:
    from playwright.sync_api import sync_playwright  # noqa: F401
    HAVE_PLAYWRIGHT = True
except ImportError:
    HAVE_PLAYWRIGHT = False

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not (RUN and HAVE_PLAYWRIGHT),
        reason="set RUN_E2E=1 and install playwright (+chromium) to run",
    ),
]


def _seed() -> None:
    from rl_bandit_lab.db.seed import load_seed_data, seed_formulas
    from rl_bandit_lab.db.session import get_sessionmaker

    async def go():
        async with get_sessionmaker()() as session:
            await seed_formulas(session, load_seed_data())
            await session.commit()

    asyncio.run(go())


@pytest.fixture(scope="module")
def live_server():
    from rl_bandit_lab.db import local_pg

    local_pg.bootstrap()
    # ensure tables exist, then seed
    subprocess.run(
        ["rl_bandit_lab_env/bin/alembic", "upgrade", "head"],
        cwd=str(PROJECT_ROOT), check=True,
    )
    _seed()

    port = 8011
    # the fixture owns the server + db lifecycle here, so disable the
    # close-the-tab self-shutdown and local-db management in the child.
    env = {
        **os.environ,
        "PYTHONPATH": "src",
        "SHUTDOWN_ON_LAST_DISCONNECT": "false",
        "MANAGE_LOCAL_DB": "false",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "rl_bandit_lab.web.app:app",
         "--port", str(port), "--log-level", "warning"],
        cwd=str(PROJECT_ROOT), env=env,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    try:
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_full_flow(live_server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # browser not installed
            pytest.skip(f"playwright chromium unavailable: {exc}")
        page = browser.new_page()

        # landing -> create a bandit -> lab
        page.goto(live_server + "/")
        page.fill("#n_arms", "3")
        page.select_option("#algorithm", "ucb1")
        page.click("#setup-form button[type=submit]")
        page.wait_for_url("**/lab/**")

        # two manual steps advance the counter (proves DB-backed reconstruction)
        page.click("#step")
        page.wait_for_function("document.getElementById('step-no').textContent === '1'")
        page.click("#step")
        page.wait_for_function("document.getElementById('step-no').textContent === '2'")
        assert page.inner_text("#step-no") == "2"

        # gridworld -> auto-sweep to convergence
        page.goto(live_server + "/gridworld")
        page.wait_for_selector("#grid .cell")
        page.click("#play")
        page.wait_for_selector("#conv.ok", timeout=20000)
        assert "converged" in page.inner_text("#conv")

        browser.close()
