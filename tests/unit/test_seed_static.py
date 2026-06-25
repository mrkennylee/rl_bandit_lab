"""Phase 3 — pure (no DB / no node) checks on the seed data: the Bellman
optimality star must be present (resolution #6)."""

from __future__ import annotations

import pytest

from rl_bandit_lab.db.seed import assert_bellman_has_star, load_seed_data


def test_real_seed_data_bellman_has_star() -> None:
    assert_bellman_has_star(load_seed_data())  # must not raise


def test_star_check_rejects_missing_star() -> None:
    bad = {"formulas": [{"key": "bellman.broken", "latex": "V(s) = max_a ..."}]}
    with pytest.raises(ValueError):
        assert_bellman_has_star(bad)
