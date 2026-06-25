"""Request bodies for the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BanditRunIn(BaseModel):
    n_arms: int = Field(ge=2, le=10)
    algorithm: Literal["epsilon_greedy", "ucb1", "thompson"] = "ucb1"
    epsilon: float = Field(0.1, ge=0.0, le=1.0)
    c: float = Field(2.0, gt=0.0)
    seed: int = 0
    true_means: list[float] | None = None  # hidden payouts; random if omitted


class GridworldRunIn(BaseModel):
    # Omit rows/cols/terminals to get the canonical Russell-Norvig 4x3 world.
    rows: int | None = None
    cols: int | None = None
    terminals: dict[str, float] | None = None  # {"r,c": reward}
    walls: list[str] | None = None             # ["r,c", ...]
    living_reward: float = -0.04
    gamma: float = 1.0
    noise: float = 0.2
    theta: float = 1e-8
