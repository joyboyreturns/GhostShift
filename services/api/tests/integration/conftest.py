from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from app.db import configure_sqlite, get_db
from app.main import app
from app.services.seed import seed


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    url = f"sqlite:///{tmp_path / 'api-test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(url, connect_args={"check_same_thread": False, "autocommit": False})
    event.listen(engine, "connect", configure_sqlite)
    with Session(engine) as db:
        seed(db)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def client(database: Engine) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        with Session(database) as session:
            yield session

    app.dependency_overrides[get_db] = override
    # Production lifespan uses the actual development DB, so seeding/migration are explicit above.
    connection = TestClient(app)
    try:
        yield connection
    finally:
        connection.close()
        app.dependency_overrides.clear()
