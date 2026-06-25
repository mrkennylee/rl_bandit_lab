"""Formula derivation retrieval — the DB end of the seeds -> DB -> API -> KaTeX
chain. Returns the formula plus its ordered derivation steps."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from rl_bandit_lab import services
from rl_bandit_lab.web.deps import get_session

router = APIRouter(tags=["formula"])


@router.get("/formula/{key}")
async def get_formula(key: str, session: AsyncSession = Depends(get_session)):
    payload = await services.formula_payload(session, key)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"unknown formula {key!r}")
    return payload
