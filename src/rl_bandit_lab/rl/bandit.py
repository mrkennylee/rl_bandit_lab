"""Multi-armed bandit agents over a Bernoulli (0/1) reward model.

All three share the action-value sample average Q(a); Thompson additionally
keeps a Beta(alpha, beta) posterior. Each ``select()`` records ``last_decision``
(scores + reason_code + formula_key) for the explanation layer, and each agent
can ``snapshot()`` / ``load()`` its learned state for DB reconstruction across
the stateless HTTP boundary.
"""

from __future__ import annotations

import numpy as np


def _argmax_random(arr: np.ndarray, rng: np.random.Generator) -> int:
    arr = np.asarray(arr, dtype=float)
    winners = np.flatnonzero(arr == arr.max())
    return int(rng.choice(winners))


class BanditAgent:
    formula_key = ""

    def __init__(self, n_arms: int, seed: int | None = None) -> None:
        self.n_arms = n_arms
        self.rng = np.random.default_rng(seed)
        self.counts = np.zeros(n_arms, dtype=np.int64)
        self.values = np.zeros(n_arms, dtype=float)
        self.last_decision: dict | None = None

    def update(self, arm: int, reward: int) -> None:
        self.counts[arm] += 1
        n = self.counts[arm]
        self.values[arm] += (reward - self.values[arm]) / n

    def snapshot(self) -> dict:
        return {"counts": self.counts.tolist(), "values": self.values.tolist()}

    def load(self, snap: dict) -> "BanditAgent":
        self.counts = np.array(snap["counts"], dtype=np.int64)
        self.values = np.array(snap["values"], dtype=float)
        return self

    def select(self) -> int:  # pragma: no cover - abstract
        raise NotImplementedError


class EpsilonGreedy(BanditAgent):
    formula_key = "bandit.value_update"

    def __init__(self, n_arms: int, epsilon: float = 0.1, seed: int | None = None) -> None:
        super().__init__(n_arms, seed)
        self.epsilon = epsilon

    def select(self) -> int:
        if self.rng.random() < self.epsilon:
            arm = int(self.rng.integers(self.n_arms))
            reason = "explore"
        else:
            arm = _argmax_random(self.values, self.rng)
            reason = "exploit"
        self.last_decision = {
            "scores": self.values.tolist(),
            "reason_code": reason,
            "formula_key": self.formula_key,
            "extra": {"epsilon": self.epsilon},
        }
        return arm


class UCB1(BanditAgent):
    formula_key = "bandit.ucb"

    def __init__(self, n_arms: int, c: float = 2.0, seed: int | None = None) -> None:
        super().__init__(n_arms, seed)
        self.c = c

    def select(self) -> int:
        untried = np.flatnonzero(self.counts == 0)
        if untried.size > 0:
            arm = int(untried[0])
            # untried arm => infinite UCB bound; represent as None (JSON-safe, the
            # UI renders it as the infinity symbol).
            scores = [
                None if self.counts[a] == 0 else float(self.values[a])
                for a in range(self.n_arms)
            ]
            reason = "explore"
        else:
            t = int(self.counts.sum())
            bonus = self.c * np.sqrt(np.log(t) / self.counts)
            score_arr = self.values + bonus
            arm = _argmax_random(score_arr, self.rng)
            reason = "exploit" if arm == int(np.argmax(self.values)) else "explore"
            scores = score_arr.tolist()
        self.last_decision = {
            "scores": scores,
            "reason_code": reason,
            "formula_key": self.formula_key,
            "extra": {"c": self.c},
        }
        return arm


class ThompsonSampling(BanditAgent):
    formula_key = "bandit.thompson"

    def __init__(self, n_arms: int, seed: int | None = None) -> None:
        super().__init__(n_arms, seed)
        self.alpha = np.ones(n_arms, dtype=float)
        self.beta = np.ones(n_arms, dtype=float)

    def update(self, arm: int, reward: int) -> None:
        super().update(arm, reward)
        self.alpha[arm] += reward
        self.beta[arm] += 1 - reward

    def select(self) -> int:
        theta = self.rng.beta(self.alpha, self.beta)
        arm = _argmax_random(theta, self.rng)
        means = self.alpha / (self.alpha + self.beta)
        reason = "exploit" if arm == int(np.argmax(means)) else "explore"
        self.last_decision = {
            "scores": theta.tolist(),
            "reason_code": reason,
            "formula_key": self.formula_key,
            "extra": {"alpha": self.alpha.tolist(), "beta": self.beta.tolist()},
        }
        return arm

    def snapshot(self) -> dict:
        snap = super().snapshot()
        snap["alpha"] = self.alpha.tolist()
        snap["beta"] = self.beta.tolist()
        return snap

    def load(self, snap: dict) -> "ThompsonSampling":
        super().load(snap)
        self.alpha = np.array(snap["alpha"], dtype=float)
        self.beta = np.array(snap["beta"], dtype=float)
        return self


_REGISTRY: dict[str, type[BanditAgent]] = {
    "epsilon_greedy": EpsilonGreedy,
    "ucb1": UCB1,
    "thompson": ThompsonSampling,
}


def make_agent(
    algorithm: str,
    n_arms: int,
    params: dict | None = None,
    seed: int | None = None,
) -> BanditAgent:
    params = params or {}
    if algorithm == "epsilon_greedy":
        return EpsilonGreedy(n_arms, epsilon=params.get("epsilon", 0.1), seed=seed)
    if algorithm == "ucb1":
        return UCB1(n_arms, c=params.get("c", 2.0), seed=seed)
    if algorithm == "thompson":
        return ThompsonSampling(n_arms, seed=seed)
    raise KeyError(f"unknown algorithm: {algorithm!r}")


def rebuild_agent(
    algorithm: str,
    n_arms: int,
    params: dict | None = None,
    seed: int | None = None,
    snapshot: dict | None = None,
) -> BanditAgent:
    """Reconstruct an agent from a persisted snapshot (the DB contract)."""
    agent = make_agent(algorithm, n_arms, params, seed)
    if snapshot is not None:
        agent.load(snapshot)
    return agent
