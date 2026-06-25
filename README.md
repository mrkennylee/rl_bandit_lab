# rl_bandit_lab

An educational reinforcement-learning simulator that teaches the **RL process,
Markov Decision Processes, and the Bellman equation** live in the browser.

- **🎰 Bandit Lab** — set N slot machines; an agent (ε-greedy / UCB1 / Thompson)
  learns which arm pays best. Every auto-learning step animates a lever pull and
  shows **why** that machine was chosen, with the action-value formula derived
  step-by-step *from the database* and rendered with KaTeX.
- **🗺️ Gridworld MDP** — a full Markov Decision Process; watch **Bellman value
  iteration** sweep the grid (value heatmap + greedy-policy arrows) until it
  converges to V\*(s).
- **🔗 The Bridge** — shows that a bandit is just a *one-state MDP* (|S|=1, γ=0),
  so the Bellman optimality equation collapses into the bandit's update.

## Stack

Python 3.12 · FastAPI + SSE · HTMX-style server rendering + vanilla JS + KaTeX ·
PostgreSQL (SQLAlchemy 2.x **async** + psycopg3, Alembic) · NumPy · pytest (TDD).
Reward model is **Bernoulli (0/1)** throughout (so Thompson's Beta posterior is
consistent). The bandit agent is reconstructed from a per-pull DB snapshot on
every step — safe across the stateless HTTP boundary.

## Quickstart

Prereqs: [`uv`](https://docs.astral.sh/uv/), Node (for the KaTeX seed gate), and
`postgresql@16` (`brew install postgresql@16`).

```bash
make install     # create the Python 3.12 venv + deps + npm (katex)
make run         # self-boots local postgres + migrates + seeds, then serves
                 # at http://127.0.0.1:8080 (open the Bandit Lab, press Auto-play)
```

### Open / close the project manually

**Open (start)** — serves on `http://127.0.0.1:8080` and auto-starts everything:

```bash
make run                 # foreground; recommended
make run PORT=9000       # different port if you like
# equivalent manual command:
PYTHONPATH=src rl_bandit_lab_env/bin/python -m uvicorn rl_bandit_lab.web.app:app \
    --host 127.0.0.1 --port 8080
```

**Close (stop)** — any of these stop the app *and* the database (data stays on disk):

- **Close the browser tab(s)** — the app self-shuts-down after a few seconds.
- **Press `Ctrl+C`** in the terminal running `make run` — graceful shutdown.
- From another terminal: `make stop` (kills the server, then stops Postgres).

**If `make run` reports the port is already in use**, the app is already running.
Stop it first (`make stop`, or close the tab) then `make run` again — a second
instance refuses to start *before* it touches anything, so it can't disturb the
running instance's database.

Other targets: `make setup` (db/migrate/seed only) · `make test` · `make lint` ·
`make dev` (auto-reload, no auto-shutdown) · `make e2e`.

Manual equivalents:

```bash
source rl_bandit_lab_env/bin/activate
python -m rl_bandit_lab.db.local_pg bootstrap   # init+start local pg in ./.pgdata, create DB
alembic upgrade head                            # create tables
python -m rl_bandit_lab.db.seed                 # KaTeX-validate then seed derivations
python -m uvicorn rl_bandit_lab.web.app:app     # run
```

## Architecture

```
src/rl_bandit_lab/
  rl/           pure engine: bandit.py (ε-greedy/UCB1/Thompson), gridworld.py
                (Bellman value iteration), explain.py ("why this arm")
  db/           models.py, session.py (async, sized pool), repository.py,
                local_pg.py (project-local postgres), seed.py (YAML→KaTeX gate→DB)
  web/          app.py, routes_bandit/mdp/formula/ui.py, deps.py, schemas.py,
                templates/ (Jinja2), static/ (app.css, app.js, app_gridworld.js)
  services.py   orchestration between the RL engine and the DB
seeds/derivations.yaml   formula derivations (validated by scripts/validate_katex.mjs)
alembic/        migrations (sync psycopg; app stays async at runtime)
```

Key design points: the SSE auto-play loop opens a **session per step and releases
it during the sleep** (the pool can't be exhausted); a per-page **presence**
channel lets the server detect when the last tab closes and **shut down the app
and the database together** (a short grace ignores page-to-page navigation), so
nothing keeps running — only `./.pgdata` and `logs/` remain on disk.

## Logging

Two timestamped channels under `logs/` (gitignored):

- `logs/system/system_<ts>.log` — system-wide events
- `logs/mdc/<unit>_<ts>.mdc` — per-unit structured records (one per stream run, etc.)

## Testing

```bash
pytest                     # full suite (unit + integration)
pytest -m "not integration"  # unit only — no postgres / no Docker needed
RUN_E2E=1 pytest -m e2e    # Playwright browser e2e (opt-in; needs `playwright install chromium`)
```

- **Unit** — pure RL math + seed checks, zero DB.
- **Integration** — repository + API + SSE against an ephemeral PostgreSQL via
  `pytest-postgresql` (no Docker required; skips cleanly if no `postgres` binary).
- **E2E** — drives the real UI in a headless browser; opt-in via `RUN_E2E=1`.
