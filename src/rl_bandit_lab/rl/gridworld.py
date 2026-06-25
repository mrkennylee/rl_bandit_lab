"""Gridworld MDP with Bellman value iteration (Russell & Norvig formulation).

Reward-on-state form:  V(s) = R(s) + gamma * max_a  sum_s' P(s'|s,a) V(s')
Terminals are absorbing with V(s) = R(s). Transitions are noisy: the intended
action happens with prob (1 - noise); the agent slips to each perpendicular
direction with prob noise/2. Moving into a wall or off-grid keeps the agent put.
"""

from __future__ import annotations

State = tuple[int, int]

ACTIONS: tuple[str, ...] = ("U", "D", "L", "R")
_DELTA: dict[str, State] = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
_PERP: dict[str, tuple[str, str]] = {
    "U": ("L", "R"), "D": ("L", "R"), "L": ("U", "D"), "R": ("U", "D"),
}


class GridworldMDP:
    def __init__(
        self,
        n_rows: int,
        n_cols: int,
        terminals: dict[State, float],
        walls: set[State] | None = None,
        living_reward: float = -0.04,
        gamma: float = 1.0,
        noise: float = 0.2,
    ) -> None:
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.terminals = dict(terminals)
        self.walls = set(walls or set())
        self.living_reward = living_reward
        self.gamma = gamma
        self.noise = noise

    # --- topology -----------------------------------------------------------

    def in_bounds(self, s: State) -> bool:
        r, c = s
        return 0 <= r < self.n_rows and 0 <= c < self.n_cols

    def is_terminal(self, s: State) -> bool:
        return s in self.terminals

    def states(self) -> list[State]:
        return [
            (r, c)
            for r in range(self.n_rows)
            for c in range(self.n_cols)
            if (r, c) not in self.walls
        ]

    def reward(self, s: State) -> float:
        return self.terminals.get(s, self.living_reward)

    def _move(self, s: State, action: str) -> State:
        dr, dc = _DELTA[action]
        nxt = (s[0] + dr, s[1] + dc)
        if not self.in_bounds(nxt) or nxt in self.walls:
            return s
        return nxt

    def transitions(self, s: State, action: str) -> list[tuple[float, State]]:
        p_intended = 1.0 - self.noise
        p_side = self.noise / 2.0
        acc: dict[State, float] = {}
        for prob, act in (
            (p_intended, action),
            (p_side, _PERP[action][0]),
            (p_side, _PERP[action][1]),
        ):
            sp = self._move(s, act)
            acc[sp] = acc.get(sp, 0.0) + prob
        return [(prob, sp) for sp, prob in acc.items()]

    # --- Bellman ------------------------------------------------------------

    def value_iteration_step(
        self, v: dict[State, float]
    ) -> tuple[dict[State, float], dict[State, str | None], float]:
        new_v: dict[State, float] = {}
        policy: dict[State, str | None] = {}
        delta = 0.0
        for s in self.states():
            if self.is_terminal(s):
                new_v[s] = self.terminals[s]
                policy[s] = None
            else:
                best_q = float("-inf")
                best_a: str | None = None
                for a in ACTIONS:
                    q = sum(prob * v.get(sp, 0.0) for prob, sp in self.transitions(s, a))
                    if q > best_q:
                        best_q = q
                        best_a = a
                new_v[s] = self.reward(s) + self.gamma * best_q
                policy[s] = best_a
            delta = max(delta, abs(new_v[s] - v.get(s, 0.0)))
        return new_v, policy, delta

    def solve(
        self, theta: float = 1e-8, max_sweeps: int = 1000
    ) -> tuple[dict[State, float], dict[State, str | None], int]:
        v: dict[State, float] = {s: 0.0 for s in self.states()}
        for s, r in self.terminals.items():
            v[s] = r
        sweeps = 0
        policy: dict[State, str | None] = {}
        for _ in range(max_sweeps):
            v, policy, delta = self.value_iteration_step(v)
            sweeps += 1
            if delta < theta:
                break
        return v, policy, sweeps

    @classmethod
    def russell_norvig(cls) -> "GridworldMDP":
        """Canonical 4x3 world: +1 / -1 terminals, a wall, -0.04 living reward."""
        return cls(
            n_rows=3,
            n_cols=4,
            terminals={(0, 3): 1.0, (1, 3): -1.0},
            walls={(1, 1)},
            living_reward=-0.04,
            gamma=1.0,
            noise=0.2,
        )
