FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /usr/local/bin/uv
WORKDIR /workspace/services/api
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --locked --no-dev
COPY services/api ./
COPY fixtures /workspace/fixtures
CMD ["sh", "-c", "uv run --no-dev alembic upgrade head && uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port 8000"]
