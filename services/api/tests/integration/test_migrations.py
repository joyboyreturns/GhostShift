from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import Document, PlaybookVersion, SourceSegment
from app.services.seed import seed


def test_migration_seed_and_database_immutability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    # A second upgrade and second seed must preserve the fixture identities/counts.
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        with Session(engine) as db:
            first = seed(db)
            assert seed(db) == first
            assert db.scalar(select(func.count()).select_from(Document)) == 2
            assert db.scalar(select(func.count()).select_from(SourceSegment)) == 10
            assert db.scalar(select(func.count()).select_from(PlaybookVersion)) == 2

        statements = [
            "UPDATE documents SET title = 'tampered'",
            "DELETE FROM source_segments",
        ]
        for statement in statements:
            with pytest.raises(IntegrityError, match="immutable source"), engine.begin() as conn:
                conn.execute(text(statement))

        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE playbook_versions SET status = 'approved' WHERE id = 'night-market-v1'"
                )
            )
        with pytest.raises(IntegrityError, match="immutable approved"), engine.begin() as conn:
            conn.execute(
                text("UPDATE playbook_versions SET title = 'tampered' WHERE id = 'night-market-v1'")
            )
        with Session(engine) as db:
            document = db.get(Document, "night-market")
            assert document is not None and document.title == "Night Market Operations"
            approved = db.get(PlaybookVersion, "night-market-v1")
            assert approved is not None and approved.title == "Night Market Operations"
    finally:
        engine.dispose()


def test_policy_migration_roundtrip_preserves_existing_records_and_immutability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'policy-roundtrip.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(url)
    with Session(engine) as db:
        seed(db)
    command.downgrade(config, "0002")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM documents")) == 2
        assert connection.scalar(text("SELECT count(*) FROM scenarios")) == 2
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM playbook_versions")) == 2
        assert (
            connection.scalar(
                text("SELECT count(*) FROM playbook_versions WHERE parent_version_id IS NOT NULL")
            )
            == 0
        )
    with pytest.raises(IntegrityError, match="immutable source"), engine.begin() as connection:
        connection.execute(text("UPDATE documents SET title='tampered'"))
    engine.dispose()
