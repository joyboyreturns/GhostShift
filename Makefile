.PHONY: install dev api web seed test lint typecheck format e2e e2e-public prepare-demo clean-demo engine-demo
install:
	cd apps/web && npm ci
	cd services/api && uv sync --locked
seed:
	cd services/api && uv run alembic upgrade head && uv run python -m app.services.seed
dev: seed
	./scripts/dev.sh
api:
	cd services/api && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
web:
	cd apps/web && npm run dev
test:
	cd services/api && uv run pytest
	cd apps/web && npm test
lint:
	cd services/api && uv run ruff check . && uv run ruff format --check .
	cd apps/web && npm run lint
typecheck:
	cd services/api && uv run mypy app
	cd apps/web && npm run typecheck
format:
	cd services/api && uv run ruff check --fix . && uv run ruff format .
	cd apps/web && npm run format
e2e:
	cd apps/web && npm run test:e2e
engine-demo:
	cd services/api && uv run python -m app.engine.demo

e2e-public:
	cd apps/web && npm run test:public
prepare-demo:
	cd services/api && uv run python -m app.services.demo_admin prepare
clean-demo:
	cd services/api && uv run python -m app.services.demo_admin cleanup
