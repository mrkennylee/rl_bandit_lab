"""SQLAlchemy 2.x ORM models. Reward model is Bernoulli (0/1) — enforced by a
CHECK constraint on pull.reward; arm_truth.true_mean is a probability in [0, 1].
Agent state survives the stateless HTTP boundary via pull.state_snapshot (JSONB).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- reference / seed tables -----------------------------------------------

class Formula(Base):
    __tablename__ = "formula"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    latex: Mapped[str] = mapped_column(Text)
    plain_explain: Mapped[str] = mapped_column(Text)

    steps: Mapped[list["DerivationStep"]] = relationship(
        back_populates="formula",
        cascade="all, delete-orphan",
        order_by="DerivationStep.step_no",
    )


class DerivationStep(Base):
    __tablename__ = "derivation_step"
    __table_args__ = (
        UniqueConstraint("formula_id", "step_no", name="uq_derivation_formula_step"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    formula_id: Mapped[int] = mapped_column(
        ForeignKey("formula.id", ondelete="CASCADE"), index=True
    )
    step_no: Mapped[int] = mapped_column(Integer)
    latex: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text, default="")

    formula: Mapped["Formula"] = relationship(back_populates="steps")


# --- run / recorded tables --------------------------------------------------

class SimRun(Base):
    __tablename__ = "sim_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(16))  # 'bandit' | 'gridworld'
    n_arms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    algorithm: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict] = mapped_column(JSONB, default=dict)  # incl. rng_seed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ArmTruth(Base):
    __tablename__ = "arm_truth"
    __table_args__ = (
        CheckConstraint("true_mean >= 0 AND true_mean <= 1", name="ck_arm_truth_prob"),
        UniqueConstraint("run_id", "arm_index", name="uq_arm_truth_run_arm"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("sim_run.id", ondelete="CASCADE"), index=True
    )
    arm_index: Mapped[int] = mapped_column(Integer)
    true_mean: Mapped[float] = mapped_column(Numeric(7, 6, asdecimal=False))


class Pull(Base):
    __tablename__ = "pull"
    __table_args__ = (
        CheckConstraint("reward IN (0, 1)", name="ck_pull_reward_bernoulli"),
        UniqueConstraint("run_id", "step_no", name="uq_pull_run_step"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("sim_run.id", ondelete="CASCADE"), index=True
    )
    step_no: Mapped[int] = mapped_column(Integer)
    arm_chosen: Mapped[int] = mapped_column(Integer)
    reward: Mapped[int] = mapped_column(SmallInteger)
    q_estimate: Mapped[float] = mapped_column(Numeric(10, 6, asdecimal=False))
    n_selected: Mapped[int] = mapped_column(Integer)
    reason_code: Mapped[str] = mapped_column(String(16))  # 'explore' | 'exploit'
    explain: Mapped[dict] = mapped_column(JSONB, default=dict)
    state_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MdpIteration(Base):
    __tablename__ = "mdp_iteration"
    __table_args__ = (
        UniqueConstraint("run_id", "sweep_no", name="uq_mdp_run_sweep"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("sim_run.id", ondelete="CASCADE"), index=True
    )
    sweep_no: Mapped[int] = mapped_column(Integer)
    max_delta: Mapped[float] = mapped_column(Numeric(12, 8, asdecimal=False))
    values: Mapped[dict] = mapped_column(JSONB, default=dict)   # {"r,c": value}
    policy: Mapped[dict] = mapped_column(JSONB, default=dict)   # {"r,c": "U/D/L/R"}
