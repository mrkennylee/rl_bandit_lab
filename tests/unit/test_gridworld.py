"""Phase 1 TDD — Gridworld MDP / Bellman value iteration.

Test 5: a hand-computed single Bellman sweep.
Test 6: convergence to the canonical Russell & Norvig 4x3 optimal policy.
"""

from __future__ import annotations

from rl_bandit_lab.rl.gridworld import GridworldMDP


def test_single_bellman_sweep_hand_computed() -> None:
    # 1x2 deterministic corridor; (0,1) is a +1 terminal, no living cost.
    g = GridworldMDP(
        n_rows=1, n_cols=2,
        terminals={(0, 1): 1.0}, walls=set(),
        living_reward=0.0, gamma=1.0, noise=0.0,
    )
    v0 = {(0, 0): 0.0, (0, 1): 1.0}  # terminal value seeded
    v1, policy, delta = g.value_iteration_step(v0)
    assert v1[(0, 0)] == 1.0       # R -> terminal worth 1
    assert v1[(0, 1)] == 1.0       # terminal stays
    assert policy[(0, 0)] == "R"
    assert delta == 1.0            # (0,0) moved 0 -> 1


def test_value_iteration_converges_to_russell_norvig_policy() -> None:
    g = GridworldMDP.russell_norvig()
    _v, policy, sweeps = g.solve(theta=1e-8, max_sweeps=1000)
    expected = {
        (0, 0): "R", (0, 1): "R", (0, 2): "R",
        (1, 0): "U",              (1, 2): "U",
        (2, 0): "U", (2, 1): "L", (2, 2): "L", (2, 3): "L",
    }
    actual = {s: a for s, a in policy.items() if a is not None}
    assert actual == expected
    assert sweeps < 1000  # converged before the cap
