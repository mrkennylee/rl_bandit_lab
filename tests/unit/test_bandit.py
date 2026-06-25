"""Phase 1 TDD — bandit agents (Bernoulli rewards, seeded RNG).

Tests 1-3 (epsilon-greedy), 3-5 (UCB1), 4 (Thompson posterior), snapshot round-trip.
"""

from __future__ import annotations

from rl_bandit_lab.rl.bandit import (
    EpsilonGreedy,
    ThompsonSampling,
    UCB1,
    rebuild_agent,
)


# --- epsilon-greedy ---------------------------------------------------------

def test_value_update_matches_incremental_formula() -> None:
    agent = EpsilonGreedy(n_arms=2, epsilon=0.0, seed=1)
    agent.update(0, 1)  # Q0 = 1
    assert agent.values[0] == 1.0
    assert agent.counts[0] == 1
    agent.update(0, 0)  # Q0 = 1 + (0-1)/2 = 0.5
    assert agent.values[0] == 0.5
    assert agent.counts[0] == 2


def test_epsilon_zero_always_exploits_best_arm() -> None:
    agent = EpsilonGreedy(n_arms=2, epsilon=0.0, seed=1)
    agent.update(0, 0)
    agent.update(1, 1)
    assert agent.select() == 1


def test_epsilon_one_explores_uniformly() -> None:
    agent = EpsilonGreedy(n_arms=3, epsilon=1.0, seed=42)
    for _ in range(3000):
        a = agent.select()
        agent.update(a, 0)
    counts = agent.counts
    assert all(c > 0 for c in counts)
    assert all(700 <= c <= 1300 for c in counts)  # ~1000 each


# --- UCB1 -------------------------------------------------------------------

def test_ucb_tries_every_arm_before_repeating() -> None:
    agent = UCB1(n_arms=3, c=2.0, seed=1)
    chosen = []
    for _ in range(3):
        a = agent.select()
        chosen.append(a)
        agent.update(a, 0)
    assert sorted(chosen) == [0, 1, 2]


def test_ucb_picks_highest_value_when_bonuses_equal() -> None:
    agent = UCB1(n_arms=2, c=1.0, seed=1)
    agent.update(0, 0)  # counts equal -> equal exploration bonus
    agent.update(1, 1)
    assert agent.select() == 1


# --- Thompson ---------------------------------------------------------------

def test_thompson_updates_beta_posteriors() -> None:
    agent = ThompsonSampling(n_arms=2, seed=1)
    agent.update(0, 1)  # alpha0: 1->2
    agent.update(0, 0)  # beta0:  1->2
    agent.update(1, 1)  # alpha1: 1->2
    snap = agent.snapshot()
    assert snap["alpha"] == [2.0, 2.0]
    assert snap["beta"] == [2.0, 1.0]


def test_thompson_favours_arm_with_better_posterior() -> None:
    agent = ThompsonSampling(n_arms=2, seed=3)
    for _ in range(20):
        agent.update(1, 1)  # arm 1 strongly successful
    picks = [agent.select() for _ in range(200)]
    assert picks.count(1) > 180


# --- snapshot / rebuild (DB reconstruction contract) ------------------------

def test_snapshot_rebuild_round_trip_ucb() -> None:
    agent = UCB1(n_arms=3, c=2.0, seed=1)
    for _ in range(10):
        a = agent.select()
        agent.update(a, a % 2)
    snap = agent.snapshot()
    clone = rebuild_agent("ucb1", n_arms=3, params={"c": 2.0}, seed=1, snapshot=snap)
    assert clone.snapshot() == snap


def test_snapshot_rebuild_round_trip_thompson() -> None:
    agent = ThompsonSampling(n_arms=2, seed=7)
    for r in (1, 0, 1, 1, 0):
        agent.update(0, r)
    snap = agent.snapshot()
    clone = rebuild_agent("thompson", n_arms=2, seed=7, snapshot=snap)
    assert clone.snapshot() == snap
