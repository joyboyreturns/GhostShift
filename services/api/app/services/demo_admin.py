"""Explicit offline preparation, retention and verified SQLite backups. Never run migrations on requests."""

import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.workspaces import APPLICATION_ID, WorkspaceStore
from app.settings import Settings


def prepare_template(target: Path) -> None:
    target = target.resolve()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists():
        raise ValueError(
            "Template already exists; use a new path to preserve the existing snapshot"
        )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".demo-template-", suffix=".db", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    old_url = os.environ.get("DATABASE_URL")
    url = f"sqlite:///{temporary}"
    try:
        os.environ["DATABASE_URL"] = url
        config = Config()
        config.set_main_option(
            "script_location", str(Path(__file__).resolve().parents[2] / "migrations")
        )
        command.upgrade(config, "head")
        from app.services.seed import seed

        engine = create_engine(url)
        try:
            with Session(engine) as db:
                seed(db)
        finally:
            engine.dispose()
        with closing(sqlite3.connect(temporary)) as db:
            db.execute(f"PRAGMA application_id={APPLICATION_ID}")
            db.commit()
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Prepared template failed SQLite integrity verification")
        # Link is atomic and refuses to overwrite a file created by another preparer.
        os.link(temporary, target)
        target.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)
        if old_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_url


def backup_database(source: Path, destination: Path) -> None:
    source = source.resolve(strict=True)
    destination = destination.resolve()
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with (
            closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original,
            closing(sqlite3.connect(destination)) as copy,
        ):
            original.backup(copy)
            if (
                copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or copy.execute("PRAGMA foreign_key_check").fetchall()
            ):
                raise ValueError("Backup failed integrity verification")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output", type=Path)
    sub.add_parser("cleanup")
    backup = sub.add_parser("backup")
    backup.add_argument("--source", required=True, type=Path)
    backup.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        target = args.output or Path(os.getenv("PUBLIC_TEMPLATE_PATH", "data/demo-template.db"))
        prepare_template(target)
        print(
            "Clean fictional demo template prepared; existing databases were not copied or replaced."
        )
    elif args.command == "cleanup":
        store = WorkspaceStore(Settings.from_env())
        print(f"Expired workspaces removed: {store.cleanup()}")
    else:
        backup_database(args.source, args.output)
        print("SQLite backup completed and integrity/foreign-key checks passed.")


if __name__ == "__main__":
    main()
