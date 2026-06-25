PY = rl_bandit_lab_env/bin/python
ALEMBIC = rl_bandit_lab_env/bin/alembic
RUFF = rl_bandit_lab_env/bin/ruff
HOST ?= 127.0.0.1
PORT ?= 8080

.PHONY: install db migrate seed setup run dev stop test lint e2e db-stop clean

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

lint:
	$(RUFF) check src tests

db-stop:
	PYTHONPATH=src $(PY) -m rl_bandit_lab.db.local_pg stop

e2e:
	uv pip install --python $(PY) playwright
	$(PY) -m playwright install chromium
	RUN_E2E=1 $(PY) -m pytest -m e2e -q
