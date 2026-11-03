"""Real migrated, isolated SQLite workspaces: no mocked ownership or fabricated data responses."""

import asyncio
import sqlite3
import time
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from app.public_demo import DemoGuard, RateLimits
from app.services.demo_admin import backup_database, prepare_template
from app.services.workspaces import WorkspaceStore
from app.settings import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    template = tmp_path / "template.db"
    prepare_template(template)
    return Settings(
        public_demo=True,
        secret="a-local-test-key-with-at-least-32-characters",
        origin="https://demo.test",
        template=template,
        workspace_root=tmp_path / "workspaces",
        writes_per_minute=1000,
        reads_per_minute=10000,
        new_workspaces_per_hour=200,
    )


def start(client: TestClient) -> dict:
    response = client.post(
        "/api/sessions", json={"scenario_id": "night-market", "allow_draft_rehearsal": True}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_visitors_cannot_read_or_mutate_each_others_runs_sources_or_proposals(
    settings: Settings,
) -> None:
    app = create_app(settings)
    bob = TestClient(app, base_url=settings.origin)
    with TestClient(app, base_url=settings.origin) as alice:
        assert alice.get("/api/demo").json()["workspace"]["mode"] == "temporary"
        assert bob.get("/api/demo").status_code == 200
        assert alice.cookies.get(settings.cookie_name) != bob.cookies.get(settings.cookie_name)
        source = alice.post(
            "/api/documents",
            json={
                "title": "Private fictional draft",
                "content": "Only my workspace can see this test record.",
            },
        ).json()
        assert bob.get(f"/api/documents/{source['id']}").status_code == 404
        run = start(alice)
        gap = alice.post(
            f"/api/sessions/{run['id']}/choose",
            json={"choice_id": "escalate", "expected_revision": 0},
        ).json()
        choices = deepcopy(
            next(
                node["choices"]
                for node in gap["result"]["input_snapshot"]["graph"]["nodes"]
                if node["id"] == "weather"
            )
        )
        choices[0]["conditions"][1]["value"] = -1
        proposal = alice.post(
            f"/api/sessions/{run['id']}/proposals",
            json={
                "expected_revision": 1,
                "rationale": "Fictional assumption test",
                "choices": choices,
            },
        ).json()
        for path in (
            f"/api/sessions/{run['id']}",
            f"/api/sessions/{run['id']}/report",
            f"/api/proposals/{proposal['id']}",
            f"/api/playbooks/{proposal['proposed_playbook_version_id']}",
        ):
            assert bob.get(path).status_code == 404
        assert (
            bob.post(
                f"/api/sessions/{run['id']}/choose",
                json={"choice_id": "outdoor", "expected_revision": 1},
            ).status_code
            == 404
        )
        assert alice.get(f"/api/sessions/{run['id']}").json() == gap
        assert bob.get("/api/playbooks/night-market-v1").json()["status"] == "draft"
        assert alice.get(f"/api/sessions/{run['id']}/replay").json()["verified"] is True
    with sqlite3.connect(settings.template) as template:
        assert template.execute("SELECT count(*) FROM simulation_sessions").fetchone()[0] == 0
        assert template.execute("SELECT count(*) FROM documents").fetchone()[0] == 2


def test_cookie_host_origin_headers_and_reset_are_guarded(settings: Settings) -> None:
    with TestClient(create_app(settings), base_url=settings.origin) as client:
        health = client.get("/api/health")
        assert health.status_code == 200 and "set-cookie" not in health.headers
        assert not list(settings.workspace_root.glob("*.db"))
        catalog = client.get("/api/demo")
        cookie = catalog.headers["set-cookie"]
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
        assert "Path=/" in cookie and "Domain=" not in cookie
        assert catalog.headers["cache-control"] == "no-store"
        assert client.get("/docs").status_code == 404
        assert client.get("/api/demo", headers={"host": "evil.test"}).status_code == 400
        assert (
            client.post(
                "/api/sessions", headers={"origin": "https://evil.test"}, json={}
            ).status_code
            == 403
        )
        assert client.get("/api/demo", headers={"sec-fetch-site": "cross-site"}).status_code == 403
        assert (
            client.post(
                "/api/documents",
                content='{"title":"x","content":"x"}',
                headers={"content-type": "text/plain"},
            ).status_code
            == 415
        )
        run = start(client)
        previous = client.cookies.get(settings.cookie_name)
        assert client.get("/api/demo/reset").status_code == 405
        assert client.cookies.get(settings.cookie_name) == previous
        assert client.post("/api/demo/reset", json={"discard": "not allowed"}).status_code == 422
        assert client.cookies.get(settings.cookie_name) == previous
        reset = client.post("/api/demo/reset", json={})
        assert reset.status_code == 200
        assert client.cookies.get(settings.cookie_name) != previous
        assert client.get(f"/api/sessions/{run['id']}").status_code == 404
        # Reset changes access, not history or expiry in the original file.
        store = client.app.state.demo_store
        identity, expires = store.parse(previous)
        with sqlite3.connect(store.path(identity, expires)) as original:
            assert original.execute("SELECT count(*) FROM simulation_sessions").fetchone()[0] == 1


def test_tampered_expired_and_missing_workspace_tokens_fail_closed(settings: Settings) -> None:
    app = create_app(settings)
    store = app.state.demo_store
    identity, expires = store.create()
    token = store.token(identity, expires)
    with TestClient(app, base_url=settings.origin) as client:
        tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
        assert (
            client.get(
                "/api/demo", headers={"cookie": f"{settings.cookie_name}={tampered}"}
            ).status_code
            == 400
        )
        expired = store.token(identity, int(time.time()) - 1)
        assert (
            client.get(
                "/api/sessions/missing", headers={"cookie": f"{settings.cookie_name}={expired}"}
            ).status_code
            == 410
        )
        fresh = client.get("/api/demo", headers={"cookie": f"{settings.cookie_name}={expired}"})
        assert fresh.status_code == 200 and "set-cookie" in fresh.headers
        missing = store.token("f" * 32, expires)
        assert (
            client.get(
                "/api/sessions/missing", headers={"cookie": f"{settings.cookie_name}={missing}"}
            ).status_code
            == 410
        )
        assert not store.path("f" * 32, expires).exists()
        with pytest.raises(HTTPException):
            store.parse(f"../../{token}")


def test_limits_apply_across_cookie_resets_and_oversized_requests(settings: Settings) -> None:
    restricted = settings.model_copy(update={"writes_per_minute": 2, "new_workspaces_per_hour": 2})
    with TestClient(create_app(restricted), base_url=restricted.origin) as client:
        first = client.get("/api/demo")
        assert first.status_code == 200
        client.cookies.clear()
        assert client.get("/api/demo").status_code == 200
        client.cookies.clear()
        response = client.get("/api/demo")
        assert response.status_code == 429 and response.headers["retry-after"] == "3600"
    with TestClient(create_app(restricted), base_url=restricted.origin) as client:
        assert (
            client.post("/api/documents", json={"title": "A", "content": "Fictional A"}).status_code
            == 201
        )
        assert (
            client.post("/api/documents", json={"title": "B", "content": "Fictional B"}).status_code
            == 201
        )
        client.cookies.clear()
        response = client.post("/api/documents", json={"title": "C", "content": "Fictional C"})
        assert response.status_code == 429 and response.headers["retry-after"] == "60"
        assert response.headers["cache-control"] == "no-store"
    with TestClient(create_app(settings), base_url=settings.origin) as client:
        oversized = client.post(
            "/api/documents",
            content=b"x" * (settings.body_bytes + 1),
            headers={"content-type": "application/json"},
        )
        assert oversized.status_code == 413
        for content in (b'{"content":NaN}', b'{"content":"\\ud800"}', b"[" * 2000 + b"]" * 2000):
            assert (
                client.post(
                    "/api/documents", content=content, headers={"content-type": "application/json"}
                ).status_code
                == 400
            )


def test_actual_sqlite_quota_rejects_atomic_write_and_preserves_existing_data(
    settings: Settings,
) -> None:
    limited = settings.model_copy(update={"workspace_bytes": 1024 * 1024})
    with TestClient(create_app(limited), base_url=limited.origin) as client:
        client.get("/api/demo")
        successful = []
        for index in range(20):
            response = client.post(
                "/api/documents", json={"title": f"Fictional {index}", "content": "x" * 100000}
            )
            if response.status_code == 507:
                break
            assert response.status_code == 201, response.text
            successful.append(response.json()["id"])
        else:
            pytest.fail("SQLite quota was not enforced")
        assert successful
        for document_id in successful:
            assert client.get(f"/api/documents/{document_id}").status_code == 200
        store = client.app.state.demo_store
        identity, expires = store.parse(client.cookies.get(limited.cookie_name))
        path = store.path(identity, expires)
        assert path.stat().st_size <= limited.workspace_bytes
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT count(*) FROM documents").fetchone()[0] == 2 + len(successful)
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_retention_skips_inflight_workspace_then_removes_database_and_sidecars(
    settings: Settings,
) -> None:
    store = WorkspaceStore(settings)
    identity, expires = store.create()
    path = store.path(identity, expires)
    with store.lease(identity, expires):
        assert store.cleanup(expires + 1) == 0
        assert path.exists()
    Path(str(path) + "-wal").touch()
    Path(str(path) + "-shm").touch()
    assert store.cleanup(expires + 1) == 1
    assert not path.exists() and not Path(str(path) + "-wal").exists()
    assert not Path(str(path) + "-shm").exists()
    assert settings.template.exists()
    assert store.cleanup(expires + 1) == 0


def test_capacity_unmarked_directories_and_dirty_templates_are_rejected(
    settings: Settings, tmp_path: Path
) -> None:
    store = WorkspaceStore(settings.model_copy(update={"max_workspaces": 1}))
    store.create()
    with pytest.raises(HTTPException) as capacity:
        store.create()
    assert capacity.value.status_code == 503
    unmarked = tmp_path / "unmarked"
    unmarked.mkdir()
    (unmarked / "keep.txt").write_text("User-owned record")
    with pytest.raises(ValueError, match="unmarked"):
        WorkspaceStore(settings.model_copy(update={"workspace_root": unmarked}))
    assert (unmarked / "keep.txt").exists()
    with pytest.raises(ValueError, match="already exists"):
        prepare_template(settings.template)
    with sqlite3.connect(settings.template) as db:
        db.execute("PRAGMA application_id=0")
    with pytest.raises(ValueError, match="unmarked database"):
        WorkspaceStore(settings)


def test_backup_is_consistent_verified_and_never_overwrites(
    settings: Settings, tmp_path: Path
) -> None:
    store = WorkspaceStore(settings)
    identity, expires = store.create()
    source = store.path(identity, expires)
    destination = tmp_path / "backup.db"
    backup_database(source, destination)
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT count(*) FROM documents").fetchone()[0] == 2
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with pytest.raises(FileExistsError):
        backup_database(source, destination)
    assert destination.stat().st_mode & 0o777 == 0o600


def test_public_configuration_requires_secret_https_and_safe_storage(settings: Settings) -> None:
    for patch in (
        {"secret": "short"},
        {"origin": "http://demo.test"},
        {"origin": "https://demo.test/"},
        {"origin": "https://user:pass@demo.test"},
        {"cookie_secure": False},
        {"template": settings.workspace_root / "unsafe.db"},
    ):
        with pytest.raises(ValidationError):
            Settings.model_validate({**settings.model_dump(), **patch})


def test_rate_limit_memory_is_bounded() -> None:
    limiter = RateLimits()
    assert limiter.allow("one", "read", 1, 60)
    assert not limiter.allow("one", "read", 1, 60)
    for index in range(10000):
        limiter.allow(str(index), "read", 1, 60)
    assert len(limiter.buckets) == 10000
    assert not limiter.allow("another", "read", 1, 60)


def test_streaming_bodies_cannot_bypass_limit_or_timeout() -> None:
    async def check(slow: bool) -> None:
        called = False
        messages = []

        async def app(scope, receive, send):
            nonlocal called
            called = True

        async def receive():
            if slow:
                await asyncio.sleep(0.1)
            return {"type": "http.request", "body": b"x" * 800, "more_body": True}

        async def send(message):
            messages.append(message)

        guard = DemoGuard(app, Settings(body_bytes=1024, body_timeout=0.01))
        await guard(
            {
                "type": "http",
                "path": "/api/documents",
                "method": "POST",
                "headers": [(b"content-type", b"application/json"), (b"content-length", b"1")],
            },
            receive,
            send,
        )
        assert not called
        assert messages[0]["status"] == (408 if slow else 413)

    asyncio.run(check(False))
    asyncio.run(check(True))


def test_schema_changes_fail_closed_without_migrating_a_live_workspace(settings: Settings) -> None:
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        session = start(client)
        store = app.state.demo_store
        identity, expires = store.parse(client.cookies.get(settings.cookie_name))
        path = store.path(identity, expires)
        with sqlite3.connect(path) as db:
            db.execute("UPDATE alembic_version SET version_num='old-schema'")
        response = client.get(f"/api/sessions/{session['id']}")
        assert (
            response.status_code == 409
            and "demo was updated" in response.json()["error"]["message"]
        )
        with sqlite3.connect(path) as db:
            assert (
                db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "old-schema"
            )
        assert client.post("/api/demo/reset", json={}).status_code == 200
        assert client.get("/api/playbooks/night-market-v1").status_code == 200


def test_maintenance_failures_are_visible_and_stop_public_writes(settings: Settings) -> None:
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        app.state.demo_store.maintenance_failed = True
        assert client.get("/api/health").status_code == 503
        assert client.post("/api/documents", json={"title": "x", "content": "x"}).status_code == 503
        app.state.demo_store.maintenance_failed = False
        assert client.get("/api/health").status_code == 200


def test_backup_restores_replay_and_cannot_be_reused_as_a_public_template(
    settings: Settings, tmp_path: Path
) -> None:
    from sqlalchemy.orm import Session

    from app.db import workspace_engine
    from app.services.simulation import replay, session_output

    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        session = start(client)
        gap = client.post(
            f"/api/sessions/{session['id']}/choose",
            json={"choice_id": "escalate", "expected_revision": 0},
        ).json()
        store = app.state.demo_store
        identity, expires = store.parse(client.cookies.get(settings.cookie_name))
        destination = tmp_path / "restored-snapshot.db"
        backup_database(store.path(identity, expires), destination)
        restored = workspace_engine(str(destination))
        try:
            with Session(restored) as db:
                assert session_output(db, session["id"]).model_dump(mode="json") == gap
                assert replay(db, session["id"]).verified is True
        finally:
            restored.dispose()
        with pytest.raises(ValueError, match="private or reviewed data"):
            WorkspaceStore(settings.model_copy(update={"template": destination}))


def test_a_marked_workspace_with_private_draft_revisions_is_not_a_clean_template(
    settings: Settings, tmp_path: Path
) -> None:
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        original = client.get("/api/playbooks/night-market-v1").json()
        response = client.post(
            "/api/playbooks/night-market-v1/revisions",
            json={
                "title": "Private draft",
                "document_id": "night-market",
                "graph": original["graph"],
            },
        )
        assert response.status_code == 201
        store = app.state.demo_store
        identity, expires = store.parse(client.cookies.get(settings.cookie_name))
        backup = tmp_path / "private-draft.db"
        backup_database(store.path(identity, expires), backup)
        with pytest.raises(ValueError, match="non-fixture versions"):
            WorkspaceStore(settings.model_copy(update={"template": backup}))


def test_a_second_api_instance_cannot_silently_bypass_in_memory_rate_limits(
    settings: Settings,
) -> None:
    first = create_app(settings)
    second = create_app(settings)
    with TestClient(first, base_url=settings.origin) as client:
        assert client.get("/api/health").status_code == 200
        with (
            pytest.raises(ValueError, match="exactly one API instance"),
            TestClient(second, base_url=settings.origin),
        ):
            pytest.fail("Second public API should not start")
    # The process lease is released on orderly shutdown.
    with TestClient(second, base_url=settings.origin) as client:
        assert client.get("/api/health").status_code == 200


def test_discovery_and_authored_scenarios_stay_inside_the_visitor_workspace(
    settings: Settings,
) -> None:
    app = create_app(settings)
    bob = TestClient(app, base_url=settings.origin)
    with TestClient(app, base_url=settings.origin) as alice:
        version = alice.get("/api/playbooks/night-market-v1").json()
        scenario = alice.post(
            "/api/scenarios",
            json={
                "playbook_version_id": version["id"],
                "title": "Alice fictional scenario",
                "initial_facts": {"vendor_delay_minutes": 45, "rain_risk": 40, "indoor_spaces": 0},
                "fictional": True,
            },
        ).json()
        alice_library = alice.get("/api/library").json()
        bob_library = bob.get("/api/library").json()
        assert scenario["id"] in {item["id"] for item in alice_library["scenarios"]}
        assert scenario["id"] not in {item["id"] for item in bob_library["scenarios"]}
        assert bob.get(f"/api/scenarios/{scenario['id']}").status_code == 404
    bob.close()
