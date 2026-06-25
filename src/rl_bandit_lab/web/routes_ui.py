"""Server-rendered pages: the setup landing and the bandit lab. Both consume the
Phase 3 JSON/SSE API from the browser (app.js)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rl_bandit_lab import services
from rl_bandit_lab.web.deps import get_session
from rl_bandit_lab.web.templating import templates

router = APIRouter(tags=["ui"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@router.get("/lab/{run_id}", response_class=HTMLResponse)
async def lab(
    run_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    run = await services.get_run(session, run_id, mode="bandit")
    if run is None:
        raise HTTPException(status_code=404, detail=f"no bandit run {run_id}")
    return templates.TemplateResponse(
        request,
        "lab.html",
        {"run_id": run_id, "n_arms": run.n_arms, "algorithm": run.algorithm},
    )


@router.get("/gridworld", response_class=HTMLResponse)
async def gridworld(request: Request):
    return templates.TemplateResponse(request, "gridworld.html", {})


@router.get("/bridge", response_class=HTMLResponse)
async def bridge(request: Request):
    return templates.TemplateResponse(request, "bridge.html", {})
