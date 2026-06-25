"""Seed formula derivations from seeds/derivations.yaml into the database.

Pipeline (resolution #4/#6):  YAML -> KaTeX validation gate -> Bellman-star
check -> DB upsert. The gate renders every LaTeX string with Node KaTeX and
refuses to seed if any fails.

CLI:  python -m rl_bandit_lab.db.seed
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from rl_bandit_lab.config import PROJECT_ROOT
from rl_bandit_lab.db import repository as repo
from rl_bandit_lab.db.models import DerivationStep, Formula
from rl_bandit_lab.db.session import get_sessionmaker

SEED_PATH = PROJECT_ROOT / "seeds" / "derivations.yaml"
KATEX_SCRIPT = PROJECT_ROOT / "scripts" / "validate_katex.mjs"

_BELLMAN_STAR = re.compile(r"V\^\*|V\^\{\*\}")


def load_seed_data(path: Path = SEED_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def collect_latex(data: dict) -> list[dict]:
    """Flatten every LaTeX string with a traceable id for the validator."""
    items: list[dict] = []
    for f in data["formulas"]:
        items.append({"id": f"{f['key']}::main", "latex": f["latex"]})
        for i, step in enumerate(f["steps"], start=1):
            items.append({"id": f"{f['key']}::step{i}", "latex": step["latex"]})
    return items


def katex_available() -> bool:
    return shutil.which("node") is not None and KATEX_SCRIPT.exists()


def validate_latex(items: list[dict]) -> list[dict]:
    """Return a list of {id, error} for strings KaTeX cannot render. Empty == ok."""
    if not katex_available():
        raise RuntimeError("node + scripts/validate_katex.mjs required for the KaTeX gate")
    proc = subprocess.run(
        ["node", str(KATEX_SCRIPT)],
        input=json.dumps(items),
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"katex validator crashed: {proc.stderr.strip()}")
    return json.loads(proc.stdout or '{"errors": []}')["errors"]


def assert_bellman_has_star(data: dict) -> None:
    """Resolution #6: every Bellman-family formula must carry the optimality star."""
    for f in data["formulas"]:
        if f["key"].startswith("bellman") and not _BELLMAN_STAR.search(f["latex"]):
            raise ValueError(f"{f['key']}: Bellman formula missing V^* optimality star")


async def seed_formulas(session: AsyncSession, data: dict) -> int:
    """Idempotent upsert by formula key. Returns the number of formulas seeded."""
    for f in data["formulas"]:
        existing = await repo.get_formula(session, f["key"])
        if existing is not None:
            await session.delete(existing)
            await session.flush()
        formula = Formula(
            key=f["key"],
            title=f["title"],
            latex=f["latex"],
            plain_explain=f.get("plain_explain", "").strip(),
        )
        formula.steps = [
            DerivationStep(step_no=i, latex=s["latex"], note=s.get("note", "").strip())
            for i, s in enumerate(f["steps"], start=1)
        ]
        session.add(formula)
    await session.flush()
    return len(data["formulas"])


async def run_seed() -> None:
    data = load_seed_data()
    assert_bellman_has_star(data)
    errors = validate_latex(collect_latex(data))
    if errors:
        raise SystemExit(f"KaTeX validation failed for: {errors}")
    maker = get_sessionmaker()
    async with maker() as session:
        count = await seed_formulas(session, data)
        await session.commit()
    print(f"seeded {count} formulas")


if __name__ == "__main__":
    asyncio.run(run_seed())
