import os
from collections.abc import Iterator
from sqlite3 import Connection

from fastapi import HTTPException, Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.services.workspaces import WorkspaceStore


class TransactionConnection(Connection):
    def rollback(self) -> None:
        # SQLITE_FULL/IO errors can make SQLite roll back automatically. Python's
        # autocommit=False then needs a transaction restored before rollback(),
        # otherwise its secondary error hides the original quota/storage failure.
        if self.autocommit is False and not self.in_transaction:
            self.execute("BEGIN")
        super().rollback()


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ghostshift.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "autocommit": False,
        "factory": TransactionConnection,
    },
)


@event.listens_for(engine, "connect")
def configure_sqlite(connection: Connection, _: object) -> None:
    # Python 3.12 transactions also cover SELECT, keeping state + ledger reads consistent.
    # SQLite requires connection PRAGMAs outside a transaction.
    previous = connection.autocommit
    connection.autocommit = True
    try:
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()
    finally:
        connection.autocommit = previous


def workspace_engine(path: str, max_bytes: int | None = None) -> Engine:
    isolated = create_engine(
        f"sqlite:///{path}",
        poolclass=NullPool,
        connect_args={
            "check_same_thread": False,
            "autocommit": False,
            "factory": TransactionConnection,
        },
    )

    def setup(connection: Connection, record: object) -> None:
        configure_sqlite(connection, record)
        if max_bytes is not None:
            previous = connection.autocommit
            connection.autocommit = True
            try:
                page_size = connection.execute("PRAGMA page_size").fetchone()[0]
                connection.execute(f"PRAGMA max_page_count={max_bytes // page_size}")
                connection.execute("PRAGMA wal_autocheckpoint=100")
            finally:
                connection.autocommit = previous

    event.listen(isolated, "connect", setup)
    return isolated


def get_db(request: Request) -> Iterator[Session]:
    store = getattr(request.state, "demo_store", None)
    if not isinstance(store, WorkspaceStore):
        with Session(engine) as session:
            yield session
        return
    if store.maintenance_failed:
        raise HTTPException(503, "Demo maintenance is unavailable. Try again shortly")
    workspace = getattr(request.state, "demo_workspace", None)
    if workspace is None:
        # Health checks see only the explicitly prepared fixture template.
        health_engine = create_engine(f"sqlite:///{store.template}", poolclass=NullPool)
        try:
            with Session(health_engine) as session:
                yield session
        finally:
            health_engine.dispose()
        return
    with store.lease(*workspace) as path:
        isolated = workspace_engine(str(path), store.settings.workspace_bytes)
        try:
            with Session(isolated) as session:
                yield session
        finally:
            isolated.dispose()
