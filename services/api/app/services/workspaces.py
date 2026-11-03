"""Anonymous demo isolation by database file. No operational history guards are bypassed."""

import fcntl
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.settings import Settings

APPLICATION_ID = 0x47534854
WORKSPACE_NAME = re.compile(r"([0-9]{10})\.([a-f0-9]{32})\.db\Z")


class WorkspaceStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.workspace_root.resolve()
        self.template = settings.template.resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        marker = self.root / ".ghostshift-workspaces"
        if not marker.exists():
            if any(self.root.iterdir()):
                raise ValueError("Refusing an unmarked, nonempty workspace directory")
            marker.write_text("GhostShift ephemeral workspaces v1\n")
        if marker.read_text() != "GhostShift ephemeral workspaces v1\n":
            raise ValueError("Invalid workspace directory marker")
        self.root.chmod(0o700)
        self.maintenance_failed = False
        self.validate_template()

    def validate_template(self) -> None:
        if not self.template.is_file():
            raise ValueError(
                "Clean demo template is missing. Run the explicit prepare-demo command"
            )
        if self.template.stat().st_size > self.settings.workspace_bytes:
            raise ValueError("Demo template exceeds the workspace quota")
        with closing(sqlite3.connect(self.template.as_uri() + "?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
                raise ValueError("Refusing to copy an unmarked database into public workspaces")
            # A template is deliberately not a copy of the user's development database.
            for table in (
                "simulation_sessions",
                "session_events",
                "rule_proposals",
                "playbook_reviews",
            ):
                if db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]:
                    raise ValueError("Demo template contains private or reviewed data")
            if db.execute("SELECT count(*) FROM documents").fetchone()[0] != 2:
                raise ValueError("Demo template must contain only the two fictional fixtures")
            if db.execute(
                "SELECT count(*) FROM playbook_versions WHERE status != 'draft'"
            ).fetchone()[0]:
                raise ValueError("Demo fixture playbooks must remain drafts")
            if (
                db.execute("SELECT count(*) FROM playbook_versions").fetchone()[0] != 2
                or db.execute("SELECT count(*) FROM scenarios").fetchone()[0] != 2
            ):
                raise ValueError("Template contains non-fixture versions or scenarios")
            from app.engine.demo import FIXTURES, fixture_input
            from app.services.segmentation import segment_document

            for name in ("night-market", "customer-support"):
                expected = fixture_input(name)
                fixture = json.loads((FIXTURES / name / "fixture.json").read_text())
                content = (FIXTURES / name / "runbook.md").read_text()
                document = db.execute(
                    "SELECT title,content,content_hash,source_type FROM documents WHERE id=?",
                    (name,),
                ).fetchone()
                if document != (
                    fixture["title"],
                    content,
                    hashlib.sha256(content.encode()).hexdigest(),
                    "markdown",
                ):
                    raise ValueError("Template source differs from the fictional fixture")
                graph = db.execute(
                    "SELECT title,version,parent_version_id,graph_json FROM playbook_versions WHERE id=? AND document_id=?",
                    (f"{name}-v1", name),
                ).fetchone()
                if (
                    not graph
                    or graph[:3] != (fixture["title"], 1, None)
                    or json.loads(graph[3]) != expected.graph.model_dump()
                ):
                    raise ValueError("Template graph differs from the fictional fixture")
                scenario = db.execute(
                    "SELECT title,description,playbook_version_id,initial_facts_json,injects_json,seed,fictional FROM scenarios WHERE id=?",
                    (name,),
                ).fetchone()
                if (
                    not scenario
                    or scenario[:3]
                    != (expected.scenario.title, fixture["description"], f"{name}-v1")
                    or json.loads(scenario[3]) != expected.scenario.initial_facts
                    or json.loads(scenario[4])
                    != [inject.model_dump() for inject in expected.scenario.injects]
                    or scenario[5:] != (expected.scenario.seed, 1)
                ):
                    raise ValueError("Template scenario differs from the fictional fixture")
                segments = db.execute(
                    "SELECT id,ordinal,text,start_offset,end_offset FROM source_segments WHERE document_id=? ORDER BY ordinal",
                    (name,),
                ).fetchall()
                if segments != [
                    (
                        segment.id,
                        segment.ordinal,
                        segment.text,
                        segment.start_offset,
                        segment.end_offset,
                    )
                    for segment in segment_document(name, content)
                ]:
                    raise ValueError("Template evidence differs from the fictional fixture")
            from alembic.config import Config
            from alembic.script import ScriptDirectory

            config = Config()
            config.set_main_option(
                "script_location", str(Path(__file__).resolve().parents[2] / "migrations")
            )
            head = ScriptDirectory.from_config(config).get_current_head()
            self.schema_revision = head
            if db.execute("SELECT version_num FROM alembic_version").fetchone()[0] != head:
                raise ValueError("Demo template schema is outdated. Prepare a fresh template")

    def token(self, identity: str, expires: int) -> str:
        payload = f"{expires}.{identity}"
        signature = hmac.new(
            self.settings.secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return f"{payload}.{signature}"

    def parse(self, token: str, now: int | None = None) -> tuple[str, int]:
        parts = token.split(".")
        if re.fullmatch(r"[0-9]{10}\.[a-f0-9]{32}\.[a-f0-9]{64}", token) is None:
            raise HTTPException(400, "Invalid demo workspace. Reload Explore demo")
        expires = int(parts[0])
        identity = parts[1]
        expected = self.token(identity, expires)
        if not hmac.compare_digest(token, expected):
            raise HTTPException(400, "Invalid demo workspace. Reload Explore demo")
        current = int(time.time()) if now is None else now
        if expires <= current:
            raise HTTPException(
                410, "This temporary workspace expired. Open Explore demo to start again"
            )
        if expires > current + self.settings.ttl_seconds + 60:
            raise HTTPException(400, "Invalid demo workspace expiration")
        return identity, expires

    def path(self, identity: str, expires: int) -> Path:
        name = f"{expires}.{identity}.db"
        if not WORKSPACE_NAME.fullmatch(name):
            raise ValueError("Invalid workspace identity")
        return self.root / name

    @contextmanager
    def server_lease(self) -> Iterator[None]:
        with (self.root / ".server.lock").open("a+b") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError(
                    "Public demo requires exactly one API instance per workspace directory"
                ) from exc
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    @contextmanager
    def _directory_lock(self) -> Iterator[None]:
        with (self.root / ".allocation.lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def create(self, now: int | None = None) -> tuple[str, int]:
        current = int(time.time()) if now is None else now
        expires = current + self.settings.ttl_seconds
        identity = uuid4().hex
        target = self.path(identity, expires)
        with self._directory_lock():
            self._cleanup(current)
            if (
                sum(1 for path in self.root.glob("*.db") if WORKSPACE_NAME.fullmatch(path.name))
                >= self.settings.max_workspaces
            ):
                raise HTTPException(503, "The demo is at capacity. Please try again later")
            # Exclusive creation prevents replacing any existing file, even with an ID collision.
            descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            try:
                with (
                    closing(
                        sqlite3.connect(self.template.as_uri() + "?mode=ro", uri=True)
                    ) as source,
                    closing(sqlite3.connect(target)) as destination,
                ):
                    source.backup(destination)
                if target.stat().st_size > self.settings.workspace_bytes:
                    raise ValueError("Demo template exceeds the workspace quota")
            except BaseException:
                target.unlink(missing_ok=True)
                raise
        return identity, expires

    @contextmanager
    def lease(self, identity: str, expires: int) -> Iterator[Path]:
        path = self.path(identity, expires)
        with Path(str(path) + ".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
            try:
                if expires <= int(time.time()) or not path.is_file():
                    raise HTTPException(
                        410,
                        "This temporary workspace is unavailable. Open Explore demo to start again",
                    )
                try:
                    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as metadata:
                        revision = metadata.execute(
                            "SELECT version_num FROM alembic_version"
                        ).fetchone()[0]
                except sqlite3.Error as exc:
                    raise HTTPException(
                        503, "Workspace storage is unavailable. Try again shortly"
                    ) from exc
                if revision != self.schema_revision:
                    raise HTTPException(
                        409,
                        "The demo was updated. Start a fresh workspace; this history stays preserved until its expiry",
                    )
                yield path
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def cleanup(self, now: int | None = None) -> int:
        with self._directory_lock():
            return self._cleanup(now)

    def _cleanup(self, now: int | None = None) -> int:
        current = int(time.time()) if now is None else now
        removed = 0
        for path in self.root.glob("*.db"):
            match = WORKSPACE_NAME.fullmatch(path.name)
            if not match or int(match[1]) > current:
                continue
            lock_path = Path(str(path) + ".lock")
            with lock_path.open("a+b") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue  # An in-flight request still holds the workspace.
                try:
                    for suffix in ("-wal", "-shm", ""):
                        Path(str(path) + suffix).unlink(missing_ok=True)
                    removed += 1
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)
            lock_path.unlink(missing_ok=True)
        return removed
