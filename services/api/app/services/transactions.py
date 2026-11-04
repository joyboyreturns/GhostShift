"""Bounded retries of SQLite WAL snapshot conflicts before a transaction commits.

A commit listener prevents replaying a successful write if response verification later fails.
Optimistic revision checks run again in each fresh transaction; they are never bypassed.
"""

from collections.abc import Callable
from functools import wraps
from sqlite3 import SQLITE_BUSY, SQLITE_FULL
from time import sleep

from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Total backoff is about 1.3s: enough for a slow writer to commit before a stale snapshot is retried.
MAX_ATTEMPTS = 8


def sqlite_write[**P, T](operation: Callable[P, T]) -> Callable[P, T]:
    @wraps(operation)
    def execute(*args: P.args, **kwargs: P.kwargs) -> T:
        db = kwargs.get("db")
        if not isinstance(db, Session):
            raise TypeError("HTTP write adapters must receive their database by keyword")
        committed = False

        def mark_committed(_: Session) -> None:
            nonlocal committed
            committed = True

        event.listen(db, "after_commit", mark_committed)
        try:
            for attempt in range(MAX_ATTEMPTS):
                try:
                    return operation(*args, **kwargs)
                except OperationalError as exc:
                    db.rollback()
                    if (
                        not committed
                        and attempt < MAX_ATTEMPTS - 1
                        and getattr(exc.orig, "sqlite_errorcode", 0) & 0xFF == SQLITE_BUSY
                    ):
                        sleep(min(0.02 * 2**attempt, 0.25))
                        continue
                    if (
                        not committed
                        and getattr(exc.orig, "sqlite_errorcode", 0) & 0xFF == SQLITE_FULL
                    ):
                        raise HTTPException(
                            507,
                            "Workspace storage limit reached. Export your reports before starting a fresh demo workspace",
                        ) from exc
                    message = (
                        "The write was saved, but its response could not be verified. Reload before continuing."
                        if committed
                        else "Database busy or unavailable. Reload before retrying the write."
                    )
                    raise HTTPException(503, message) from exc
            raise AssertionError("unreachable retry state")
        finally:
            event.remove(db, "after_commit", mark_committed)

    return execute
