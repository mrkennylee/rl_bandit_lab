"""Phase 1 TDD — the "why this arm" explanation builder."""

from __future__ import annotations

import pytest

from rl_bandit_lab.rl.bandit import EpsilonGreedy, UCB1
from rl_bandit_lab.rl.explain import build_explanation


def test_explain_marks_exploit_for_greedy_pick() -> None:
    agent = EpsilonGreedy(n_arms=2, epsilon=0.0, seed=1)
    agent.update(0, 0)
    agent.update(1, 1)
    arm = agent.select()
    ex = build_explanation(agent, arm)
    assert ex["reason_code"] == "exploit"
    assert ex["formula_key"] == "bandit.value_update"
    assert ex["text"]
    assert len(ex["scores"]) == 2


def test_explain_marks_explore_for_untried_ucb_arm() -> None:
    agent = UCB1(n_arms=2, c=2.0, seed=1)
    arm = agent.select()  # first selection -> an untried arm
    ex = build_explanation(agent, arm)
    assert ex["reason_code"] == "explore"
    assert ex["formula_key"] == "bandit.ucb"
    assert len(ex["scores"]) == 2


def test_explain_requires_a_prior_selection() -> None:
    agent = EpsilonGreedy(n_arms=2, epsilon=0.0, seed=1)
    with pytest.raises(ValueError):
        build_explanation(agent, 0)
