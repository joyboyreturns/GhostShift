FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 UV_NO_SYNC=1
WORKDIR /workspace/services/api
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --locked --no-dev
COPY services/api/app ./app
COPY services/api/migrations ./migrations
COPY services/api/alembic.ini ./
COPY fixtures /workspace/fixtures
RUN groupadd --gid 10001 ghostshift && useradd --uid 10001 --gid 10001 --no-create-home ghostshift && mkdir /data && chown ghostshift:ghostshift /data
USER ghostshift
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*", "--limit-concurrency", "40"]
