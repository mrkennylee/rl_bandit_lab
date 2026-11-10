PY = rl_bandit_lab_env/bin/python
ALEMBIC = rl_bandit_lab_env/bin/alembic
RUFF = rl_bandit_lab_env/bin/ruff
HOST ?= 127.0.0.1
PORT ?= 8080

.PHONY: install db migrate seed setup run dev stop test check lint e2e db-stop clean

install:
	uv venv rl_bandit_lab_env --python 3.12
	uv pip install --python $(PY) -r requirements.txt
	npm install

db:
	PYTHONPATH=src $(PY) -m rl_bandit_lab.db.local_pg bootstrap

migrate:
	$(ALEMBIC) upgrade head

seed:
	PYTHONPATH=src $(PY) -m rl_bandit_lab.db.seed

setup: db migrate seed

# run: boots the local db, serves on http://$(HOST):$(PORT), and stops everything
# when the last tab closes. (no --reload: the reloader would restart the server
# we intentionally SIGTERM.)  Override the port with:  make run PORT=9000
run:
	PYTHONPATH=src $(PY) -m uvicorn rl_bandit_lab.web.app:app --host $(HOST) --port $(PORT)

# dev: auto-reload for development (close-the-tab shutdown is disabled here)
dev:
	SHUTDOWN_ON_LAST_DISCONNECT=false PYTHONPATH=src $(PY) -m uvicorn rl_bandit_lab.web.app:app --host $(HOST) --port $(PORT) --reload

# stop: stop the app if it's running in the background, then stop the database
stop:
	-pkill -f "uvicorn rl_bandit_lab.web.app"
	PYTHONPATH=src $(PY) -m rl_bandit_lab.db.local_pg stop

test:
	$(PY) -m pytest -q

# check: the project's one check command (see README "Check command").
# Installs deps if the venv is missing or requirements changed, refuses to run
# without postgres/node (so integration + KaTeX tests can't silently skip), then
# runs the full suite with a coverage report. Exit 0 only if every test passes.
DEPS_STAMP = rl_bandit_lab_env/.deps-stamp

$(DEPS_STAMP): requirements.txt package-lock.json
	test -x $(PY) || uv venv rl_bandit_lab_env --python 3.12
	uv pip install --python $(PY) -r requirements.txt
	npm install
	touch $@

check: $(DEPS_STAMP)
	@PYTHONPATH=src $(PY) -c "import sys; from rl_bandit_lab.db.local_pg import postgres_bin_dir; sys.exit(0 if postgres_bin_dir() else 'check: postgres binaries not found (brew install postgresql@16)')"
	@command -v node >/dev/null || { echo "check: node not found (needed for KaTeX seed tests)"; exit 1; }
	$(PY) -m pytest -q -rs --cov --cov-report=term

lint:
	$(RUFF) check src tests

db-stop:
	PYTHONPATH=src $(PY) -m rl_bandit_lab.db.local_pg stop

e2e:
	uv pip install --python $(PY) playwright
	$(PY) -m playwright install chromium
	RUN_E2E=1 $(PY) -m pytest -m e2e -q
