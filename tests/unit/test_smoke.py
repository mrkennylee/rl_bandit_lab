"""Phase 0 smoke tests: app boots, /health responds, both log channels write."""

from __future__ import annotations

import httpx

from rl_bandit_lab.config import get_settings
from rl_bandit_lab.logging.mdc_logger import MdcLogger
from rl_bandit_lab.logging.system_logger import get_system_logger
from rl_bandit_lab.web.app import create_app


async def test_health_endpoint_ok() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "rl_bandit_lab"


def test_system_logger_creates_timestamped_file() -> None:
    log = get_system_logger()
    log.info("smoke: system log line")
    files = list(get_settings().system_log_dir.glob("system_*.log"))
    assert files, "expected a timestamped system_*.log file"


def test_mdc_logger_writes_frontmatter_and_lines() -> None:
    with MdcLogger("smoke_test", run_id=0, algorithm="none") as m:
        m.line("step 1 | arm 0 | reward 1 | reason explore")
        path = m.path
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "unit: smoke_test" in content
    assert "run_id: 0" in content
    assert "step 1 | arm 0 | reward 1 | reason explore" in content
    assert content.rstrip().endswith("_")  # _ended: ..._ footer
