"""Builds the "why this arm was chosen" object the UI renders alongside the math."""

from __future__ import annotations

from rl_bandit_lab.rl.bandit import BanditAgent

_REASON_TEXT = {
    "explore": "EXPLORE — pick an uncertain arm to gather information about its payout.",
    "exploit": "EXPLOIT — pick the arm that currently looks best to maximise reward.",
}


def build_explanation(agent: BanditAgent, arm: int) -> dict:
    decision = agent.last_decision
    if decision is None:
        raise ValueError("call agent.select() before build_explanation()")
    reason = decision["reason_code"]
    return {
        "arm": int(arm),
        "reason_code": reason,
        "formula_key": decision["formula_key"],
        "scores": decision["scores"],
        "extra": decision.get("extra", {}),
        "text": f"Arm {arm}: {_REASON_TEXT[reason]}",
    }
