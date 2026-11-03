"""Real migrated SQLite/API tests; the existing deterministic engine is reused unchanged."""

import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.engine.interfaces import LogicalEvent
from app.models.entities import PlaybookVersion, SessionEvent, SimulationSession
from app.services import simulation


def start(client: TestClient, scenario: str = "night-market") -> dict:
    response = client.post(
        "/api/sessions", json={"scenario_id": scenario, "allow_draft_rehearsal": True}
    )
    assert response.status_code == 201, response.text
    return response.json()


def choose(client: TestClient, session: dict, choice: str) -> dict:
    response = client.post(
        f"/api/sessions/{session['id']}/choose",
        json={
            "choice_id": choice,
            "expected_revision": session["revision"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_draft_rehearsal_is_explicit_and_cannot_approve_a_playbook(client: TestClient) -> None:
    scenario = client.get("/api/scenarios/night-market")
    assert scenario.status_code == 200 and scenario.json()["fictional"]
    assert client.get("/api/scenarios/missing").status_code == 404
    assert client.post("/api/sessions", json={"scenario_id": "night-market"}).status_code == 409
    assert (
        client.post(
            "/api/sessions", json={"scenario_id": "night-market", "playbook_authority": "approved"}
        ).status_code
        == 422
    )
    session = start(client)
    assert session["result"]["playbook_authority"] == "draft"
    assert client.get("/api/playbooks/night-market-v1").json()["status"] == "draft"


def test_choice_appends_events_and_reaches_real_uncovered_path(client: TestClient) -> None:
    initial = start(client)
    assert initial["status"] == "awaiting_decision" and initial["revision"] == 0
    assert len(initial["events"]) == 3
    assert not any(event["event_type"] == "run_terminated" for event in initial["events"])
    result = choose(client, initial, "escalate")
    assert result["status"] == "uncovered" and result["revision"] == 1
    assert result["current_node_id"] == "weather"
    assert result["result"]["final_facts"] == {
        "vendor_delay_minutes": 45,
        "rain_risk": 85,
        "indoor_spaces": 0,
    }
    assert result["events"][: len(initial["events"])] == initial["events"]
    assert [event["sequence"] for event in result["events"]] == list(range(len(result["events"])))
    assert client.get(f"/api/sessions/{result['id']}").json() == result
    assert all(event["playbook_authority"] == "draft" for event in result["events"])


def test_duplicate_stale_invalid_and_terminal_choices_do_not_write(client: TestClient) -> None:
    initial = start(client)
    invalid = {"choice_id": "absent", "expected_revision": 0}
    assert client.post(f"/api/sessions/{initial['id']}/choose", json=invalid).status_code == 422
    assert client.get(f"/api/sessions/{initial['id']}").json() == initial
    invalid["expected_revision"] = 0.0
    assert client.post(f"/api/sessions/{initial['id']}/choose", json=invalid).status_code == 422
    result = choose(client, initial, "escalate")
    for revision in (0, 1):
        response = client.post(
            f"/api/sessions/{initial['id']}/choose",
            json={"choice_id": "escalate", "expected_revision": revision},
        )
        assert response.status_code == 409
        assert client.get(f"/api/sessions/{initial['id']}").json() == result


def test_concurrent_choice_submissions_only_commit_once(client: TestClient) -> None:
    initial = start(client)

    def submit(choice: str) -> int:
        return client.post(
            f"/api/sessions/{initial['id']}/choose",
            json={
                "choice_id": choice,
                "expected_revision": 0,
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(submit, ["escalate", "routine"]))
    assert sorted(statuses) == [200, 409]
    result = client.get(f"/api/sessions/{initial['id']}").json()
    assert result["revision"] == 1
    assert (
        len([event for event in result["events"] if event["event_type"] == "decision_selected"])
        == 1
    )


def test_seeded_support_uses_same_engine_and_stops_on_overlap(client: TestClient) -> None:
    session = start(client, "customer-support")
    assert session["status"] == "overlap" and session["revision"] == 0
    assert session["result"]["checkpoint"]["matching_choice_ids"] == ["standard", "promo"]
    assert (
        client.post(
            f"/api/sessions/{session['id']}/choose",
            json={"choice_id": "standard", "expected_revision": 0},
        ).status_code
        == 409
    )


def test_replay_reexecutes_pinned_input_and_checks_stored_ledger(client: TestClient) -> None:
    initial = start(client)
    for advance in (False, True):
        session = choose(client, initial, "escalate") if advance else initial
        response = client.get(f"/api/sessions/{session['id']}/replay")
        assert response.status_code == 200
        assert response.json()["verified"] is True
        assert response.json()["event_count"] == len(session["events"])
        assert response.json()["last_state_hash"] == session["events"][-1]["state_hash"]


def test_fork_preserves_parent_and_supports_independent_alternate_choice(
    client: TestClient,
) -> None:
    parent = choose(client, start(client), "escalate")
    response = client.post(f"/api/sessions/{parent['id']}/fork", json={"event_index": 2})
    assert response.status_code == 201
    child = response.json()
    assert child["id"] != parent["id"] and child["parent_session_id"] == parent["id"]
    assert child["fork_event_index"] == 2 and child["revision"] == 0
    assert child["status"] == "awaiting_decision"
    assert [event["state_hash"] for event in child["events"]] == [
        event["state_hash"] for event in parent["events"][:3]
    ]
    alternate = choose(client, child, "routine")
    assert alternate["status"] == "uncovered"
    assert len(alternate["result"]["deviations"]) == 1
    assert client.get(f"/api/sessions/{parent['id']}").json() == parent
    assert client.get(f"/api/sessions/{child['id']}/replay").json()["verified"]


def test_fork_at_gap_stays_unresolved_and_invalid_checkpoints_are_rejected(
    client: TestClient,
) -> None:
    parent = choose(client, start(client), "escalate")
    for index in (-1, 0, 1000):
        assert (
            client.post(
                f"/api/sessions/{parent['id']}/fork", json={"event_index": index}
            ).status_code
            == 422
        )
    index = next(
        event["sequence"]
        for event in parent["events"]
        if event["event_type"] == "decision_evaluated" and event["node_id"] == "weather"
    )
    child = client.post(f"/api/sessions/{parent['id']}/fork", json={"event_index": index}).json()
    assert child["status"] == "uncovered" and child["revision"] == 0
    assert child["result"]["decisions_made"] == parent["result"]["decisions_made"]
    assert client.get(f"/api/sessions/{parent['id']}").json() == parent


def test_reports_and_comparison_derive_real_findings_and_preserve_authority(
    client: TestClient,
) -> None:
    parent = choose(client, start(client), "escalate")
    child = client.post(f"/api/sessions/{parent['id']}/fork", json={"event_index": 2}).json()
    child = choose(client, child, "routine")
    report = client.get(f"/api/sessions/{child['id']}/report").json()
    assert report["playbook_version_id"] == "night-market-v1"
    assert report["playbook_authority"] == "draft" and report["reviewed_supported_count"] == 0
    assert (
        report["decision_count"] == report["deviation_count"] == report["cited_decision_count"] == 1
    )
    assert report["uncovered_count"] == 1 and report["overlap_count"] == 0
    assert report["decisions"][0]["choice_id"] == "routine"
    assert report["findings"][0]["node_id"] == "weather"
    compared = client.get(
        "/api/sessions/compare", params={"left_id": parent["id"], "right_id": child["id"]}
    )
    assert compared.status_code == 200
    assert compared.json()["shared_event_prefix"] == 3
    assert compared.json()["left"]["deviation_count"] == 0
    assert compared.json()["right"] == report
    support = start(client, "customer-support")
    assert (
        client.get(
            "/api/sessions/compare", params={"left_id": parent["id"], "right_id": support["id"]}
        ).status_code
        == 422
    )


def test_session_survives_draft_graph_changes_with_its_original_snapshot(
    client: TestClient, database: Engine
) -> None:
    initial = start(client)
    with Session(database) as db:
        playbook = db.get(PlaybookVersion, "night-market-v1")
        assert playbook is not None
        graph = copy.deepcopy(playbook.graph_json)
        graph["nodes"][1]["label"] = "A changed draft label"
        playbook.graph_json = graph
        db.commit()
    existing = client.get(f"/api/sessions/{initial['id']}").json()
    assert existing == initial
    result = choose(client, initial, "escalate")
    assert result["status"] == "uncovered"
    newer = start(client)
    assert newer["events"][0]["context_hash"] != result["events"][0]["context_hash"]
    assert (
        client.get(
            "/api/sessions/compare", params={"left_id": initial["id"], "right_id": newer["id"]}
        ).status_code
        == 422
    )


def test_database_protects_events_scenarios_and_session_identity(
    client: TestClient, database: Engine
) -> None:
    initial = start(client)
    for statement in [
        "UPDATE session_events SET state_hash = 'tampered'",
        "DELETE FROM session_events",
        "UPDATE scenarios SET seed = 7",
        "UPDATE simulation_sessions SET document_id = 'customer-support'",
    ]:
        with pytest.raises(IntegrityError, match="immutable"), database.begin() as connection:
            connection.execute(text(statement))
    assert client.get(f"/api/sessions/{initial['id']}").json() == initial


def test_replay_detects_corrupt_materialized_state_without_rewriting_events(
    client: TestClient, database: Engine
) -> None:
    initial = start(client)
    with Session(database) as db:
        row = db.get(SimulationSession, initial["id"])
        assert row is not None
        corrupt = copy.deepcopy(row.state_json)
        corrupt["final_facts"]["rain_risk"] = 999
        db.execute(
            update(SimulationSession)
            .where(SimulationSession.id == row.id)
            .values(state_json=corrupt)
        )
        db.commit()
    assert client.get(f"/api/sessions/{initial['id']}/replay").status_code == 409
    with Session(database) as db:
        events = list(
            db.scalars(
                select(SessionEvent)
                .where(SessionEvent.session_id == initial["id"])
                .order_by(SessionEvent.sequence_number)
            )
        )
        assert [event.state_hash for event in events] == [
            event["state_hash"] for event in initial["events"]
        ]


def test_state_and_ledger_read_share_one_snapshot_during_a_write(
    client: TestClient, database: Engine
) -> None:
    initial = start(client)
    count = (
        select(func.count())
        .select_from(SessionEvent)
        .where(SessionEvent.session_id == initial["id"])
    )
    revision = select(SimulationSession.revision).where(SimulationSession.id == initial["id"])
    with database.connect() as reader:
        assert reader.scalar(count) == 3
        chosen = choose(client, initial, "escalate")
        # The existing reader sees the same revision and ledger even after the writer commits.
        assert reader.scalar(count) == 3
        assert reader.scalar(revision) == 0
    with database.connect() as reader:
        assert reader.scalar(count) == len(chosen["events"])
        assert reader.scalar(revision) == 1
        assert reader.scalar(text("PRAGMA foreign_keys")) == 1
        assert reader.scalar(text("PRAGMA journal_mode")) == "wal"


def test_failure_between_revision_claim_and_event_append_rolls_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    initial = start(client)

    def fail_append(db: Session, session_id: str, events: list[LogicalEvent]) -> None:
        raise RuntimeError("Injected storage failure")

    with monkeypatch.context() as patch:
        patch.setattr(simulation, "_append", fail_append)
        with pytest.raises(RuntimeError, match="Injected storage failure"):
            client.post(
                f"/api/sessions/{initial['id']}/choose",
                json={"choice_id": "escalate", "expected_revision": 0},
            )
    assert client.get(f"/api/sessions/{initial['id']}").json() == initial
    assert choose(client, initial, "escalate")["revision"] == 1


def test_unrelated_commit_during_choice_retries_snapshot_without_losing_revision_guard(
    client: TestClient, database: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    initial = start(client)
    unrelated = start(client)
    original = simulation._verified
    triggered = False

    def verify_then_commit(db: Session, row: SimulationSession):
        nonlocal triggered
        result = original(db, row)
        if row.id == initial["id"] and not triggered:
            triggered = True
            choose(client, unrelated, "escalate")
        return result

    monkeypatch.setattr(simulation, "_verified", verify_then_commit)
    result = choose(client, initial, "escalate")
    assert result["revision"] == 1 and result["status"] == "uncovered"
    assert (
        client.post(
            f"/api/sessions/{initial['id']}/choose",
            json={"choice_id": "routine", "expected_revision": 0},
        ).status_code
        == 409
    )
    assert client.get(f"/api/sessions/{initial['id']}").json() == result


def test_response_failure_after_commit_never_retries_a_successful_choice(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlite3 import SQLITE_BUSY, OperationalError

    from sqlalchemy.exc import OperationalError as DatabaseError

    initial = start(client)
    original = simulation._verified
    calls = 0

    def fail_response_read(db: Session, row: SimulationSession):
        nonlocal calls
        calls += 1
        if calls == 2:  # Verification after the choice + event transaction has committed.
            failure = OperationalError("database is locked")
            failure.sqlite_errorcode = SQLITE_BUSY
            raise DatabaseError("response read", {}, failure)
        return original(db, row)

    monkeypatch.setattr(simulation, "_verified", fail_response_read)
    response = client.post(
        f"/api/sessions/{initial['id']}/choose",
        json={"choice_id": "escalate", "expected_revision": 0},
    )
    assert response.status_code == 503
    assert "write was saved" in response.json()["error"]["message"]
    assert calls == 2  # No retry occurred after commit.
    stored = client.get(f"/api/sessions/{initial['id']}").json()
    assert stored["revision"] == 1 and stored["status"] == "uncovered"
    assert (
        len([event for event in stored["events"] if event["event_type"] == "decision_selected"])
        == 1
    )
