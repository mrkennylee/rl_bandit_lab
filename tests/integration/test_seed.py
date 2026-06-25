"""Phase 3 — seeding (idempotent DB upsert) + the KaTeX validation gate."""

from __future__ import annotations

import pytest

from rl_bandit_lab.db import repository as repo
from rl_bandit_lab.db.seed import (
    collect_latex,
    katex_available,
    load_seed_data,
    seed_formulas,
    validate_latex,
)

pytestmark = pytest.mark.integration


async def test_seeding_is_idempotent(db_session):
    data = load_seed_data()
    await seed_formulas(db_session, data)
    await db_session.commit()
    await seed_formulas(db_session, data)  # run again
    await db_session.commit()

    steps = await repo.get_derivation(db_session, "bandit.value_update")
    assert len(steps) == 4  # not 8 -> no duplicates
    assert await repo.get_formula(db_session, "bellman.optimality") is not None


@pytest.mark.skipif(not katex_available(), reason="node + katex not available")
def test_seed_latex_all_render():
    data = load_seed_data()
    assert validate_latex(collect_latex(data)) == []


@pytest.mark.skipif(not katex_available(), reason="node + katex not available")
def test_malformed_latex_is_rejected():
    errors = validate_latex([{"id": "bad", "latex": r"\frac{1}{"}])
    assert errors  # non-empty -> gate would block the seed
