"""Discoverability, authored rehearsals and portable evidence use real migrated API state."""

import hashlib
from copy import deepcopy

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.engine.interfaces import RunInput
from app.engine.interpreter import GhostShiftEngine


def model(client: TestClient) -> dict:
    source = client.post(
        "/api/documents",
        json={
            "title": "Fictional delivery instructions",
            "content": "Escalate vendor delays of at least 30 minutes.",
        },
    ).json()
    response = client.post(
        "/api/playbooks",
        json={
            "document_id": source["id"],
            "title": "Fictional delivery model",
            "graph": {
                "nodes": [
                    {"id": "start", "label": "Begin", "type": "start", "next_node": "delay"},
                    {
                        "id": "delay",
                        "label": "Delay threshold",
                        "type": "decision",
                        "source_refs": [source["segments"][0]["id"]],
                        "choices": [
                            {
                                "id": "escalate",
                                "label": "Escalate",
                                "destination": "end",
                                "conditions": [{"field": "delay", "operator": "gte", "value": 30}],
                                "source_refs": [source["segments"][0]["id"]],
                                "evidence_status": "cited",
                            }
                        ],
                    },
                    {"id": "end", "label": "Done", "type": "end"},
                ]
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def authored(client: TestClient, version: dict) -> dict:
    response = client.post(
        "/api/scenarios",
        json={
            "playbook_version_id": version["id"],
            "title": "Fictional vendor delay",
            "description": "An authored disruption",
            "initial_facts": {"delay": 0},
            "injects": [{"before_node_id": "delay", "facts": {"delay": 45}}],
            "seed": 123,
            "fictional": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_library_is_paginated_searchable_and_does_not_return_raw_documents_or_run_state(
    client: TestClient,
) -> None:
    version = model(client)
    scenario = authored(client, version)
    run = client.post(
        "/api/sessions", json={"scenario_id": scenario["id"], "allow_draft_rehearsal": True}
    ).json()
    page = client.get("/api/library", params={"limit": 1}).json()
    assert page["totals"] == {"documents": 3, "playbooks": 3, "scenarios": 3, "sessions": 1}
    assert (
        len(page["documents"]) == 1
        and page["documents"][0]["title"] == "Fictional delivery instructions"
    )
    assert "content" not in page["documents"][0] and "state_json" not in page["sessions"][0]
    assert (
        client.get("/api/library", params={"q": run["id"]}).json()["sessions"][0]["id"] == run["id"]
    )
    assert client.get("/api/library", params={"q": "%"}).json()["documents"] == []
    assert client.get("/api/library", params={"limit": 51}).status_code == 422
    assert client.get("/api/library", params={"offset": 10**100}).status_code == 422
    second = client.get("/api/library", params={"limit": 1, "offset": 1}).json()
    assert second["documents"][0]["id"] != page["documents"][0]["id"]


def test_an_imported_model_has_its_own_real_immutable_scenario_and_portable_report(
    client: TestClient,
) -> None:
    version = model(client)
    original = client.get(f"/api/playbooks/{version['id']}").json()
    scenario = authored(client, version)
    assert scenario["id"] not in {"night-market", "customer-support"}
    assert client.get(f"/api/scenarios/{scenario['id']}").json() == scenario
    run = client.post(
        "/api/sessions", json={"scenario_id": scenario["id"], "allow_draft_rehearsal": True}
    ).json()
    assert run["result"]["checkpoint"]["matching_choice_ids"] == ["escalate"]
    assert run["result"]["final_facts"] == {"delay": 45}
    completed = client.post(
        f"/api/sessions/{run['id']}/choose", json={"choice_id": "escalate", "expected_revision": 0}
    ).json()
    assert completed["status"] == "completed"
    report = client.get(f"/api/sessions/{run['id']}/report").json()
    assert report["source_title"] == "Fictional delivery instructions"
    assert report["evidence"][0]["text"] == "Escalate vendor delays of at least 30 minutes."
    assert (
        report["source_content_hash"]
        == hashlib.sha256(report["evidence"][0]["text"].encode()).hexdigest()
    )
    reproduced = GhostShiftEngine().run(RunInput.model_validate(report["replay_input"]))
    assert [event.model_dump(mode="json") for event in reproduced.events] == report[
        "logical_events"
    ]
    assert reproduced.final_facts == report["final_facts"]
    assert report["logical_events"][-1]["state_hash"] == report["last_state_hash"]
    assert client.get(f"/api/playbooks/{version['id']}").json() == original
    assert client.get(f"/api/playbooks/{version['id']}/scenarios").json()[0]["id"] == scenario["id"]


def test_scenario_authoring_rejects_unknown_targets_oversized_facts_and_silent_policy_fields(
    client: TestClient,
) -> None:
    version = model(client)
    payload = {
        "playbook_version_id": version["id"],
        "title": "Test",
        "initial_facts": {},
        "fictional": True,
    }
    for patch in (
        {"title": "   "},
        {"fictional": False},
        {"initial_facts": {str(i): i for i in range(65)}},
        {"initial_facts": {"field": "x" * 501}},
        {
            "initial_facts": {str(i): i for i in range(64)},
            "injects": [{"before_node_id": "delay", "facts": {"extra": 1}}],
        },
        {"seed": 0.5},
        {"id": "night-market"},
        {"playbook_authority": "approved"},
        {"playbook_version_id": "missing"},
        {"injects": [{"before_node_id": "missing", "facts": {"delay": 45}}]},
    ):
        response = client.post("/api/scenarios", json={**payload, **patch})
        assert response.status_code in {404, 422}, response.text
    source = client.post(
        "/api/documents", json={"title": "Empty model", "content": "Fictional text"}
    ).json()
    empty = client.post(f"/api/documents/{source['id']}/draft", json={"title": "Blank"}).json()
    assert (
        client.post(
            "/api/scenarios", json={**payload, "playbook_version_id": empty["id"]}
        ).status_code
        == 422
    )


def test_version_history_tracks_branches_across_sources_without_unrelated_models(
    client: TestClient,
) -> None:
    root = model(client)
    body = {"document_id": root["document_id"], "title": root["title"], "graph": root["graph"]}
    left = client.post(f"/api/playbooks/{root['id']}/revisions", json=body).json()
    right = client.post(f"/api/playbooks/{root['id']}/revisions", json=body).json()
    unrelated = client.post("/api/playbooks", json=body).json()
    source = client.post(
        "/api/documents", json={"title": "New source", "content": "Revised fictional policy"}
    ).json()
    graph = deepcopy(root["graph"])
    for node in graph["nodes"]:
        node["source_refs"] = []
        for choice in node["choices"]:
            choice["source_refs"] = []
            choice["evidence_status"] = "uncited"
    revised = client.post(
        f"/api/playbooks/{left['id']}/revisions",
        json={**body, "document_id": source["id"], "graph": graph},
    ).json()
    history = client.get(f"/api/playbooks/{revised['id']}/history").json()
    assert {version["id"] for version in history["versions"]} == {
        root["id"],
        left["id"],
        right["id"],
        revised["id"],
    }
    assert unrelated["id"] not in {version["id"] for version in history["versions"]}
    assert client.get(f"/api/documents/{root['document_id']}/models").status_code == 200
    assert client.get("/api/playbooks/missing/history").status_code == 404
    assert client.get("/api/documents/missing/models").status_code == 404


def test_corrupt_version_cycles_fail_closed(client: TestClient, database: Engine) -> None:
    version = model(client)
    with database.begin() as connection:
        connection.execute(
            text("UPDATE playbook_versions SET parent_version_id=id WHERE id=:id"),
            {"id": version["id"]},
        )
    assert client.get(f"/api/playbooks/{version['id']}/history").status_code == 409


def test_portable_report_includes_every_modeled_source_reference_and_pinned_review(
    client: TestClient,
) -> None:
    version = model(client)
    scenario = authored(client, version)
    # Draft authority remains pinned even after its model is approved later.
    draft = client.post(
        "/api/sessions", json={"scenario_id": scenario["id"], "allow_draft_rehearsal": True}
    ).json()
    approval = {
        "expected_graph_hash": version["graph_hash"],
        "reviewer": "Fictional source reviewer",
        "notes": "The threshold matches this fictional source.",
        "confirmed_source_support": True,
        "reviewed_choices": [{"node_id": "delay", "choice_id": "escalate"}],
    }
    assert client.post(f"/api/playbooks/{version['id']}/approve", json=approval).status_code == 200
    old_report = client.get(f"/api/sessions/{draft['id']}/report").json()
    assert old_report["approval"] is None and old_report["playbook_authority"] == "draft"
    reviewed = client.post("/api/sessions", json={"scenario_id": scenario["id"]}).json()
    report = client.get(f"/api/sessions/{reviewed['id']}/report").json()
    assert report["approval"]["reviewer"] == "Fictional source reviewer"
    references = {
        reference
        for node in report["replay_input"]["graph"]["nodes"]
        for reference in [
            *node["source_refs"],
            *(ref for choice in node["choices"] for ref in choice["source_refs"]),
        ]
    }
    assert references == {evidence["id"] for evidence in report["evidence"]}


def test_workspace_timestamps_explicitly_identify_utc(client: TestClient) -> None:
    version = model(client)
    scenario = authored(client, version)
    session = client.post(
        "/api/sessions", json={"scenario_id": scenario["id"], "allow_draft_rehearsal": True}
    ).json()
    assert session["created_at"].endswith("Z")
    assert all(event["created_at"].endswith("Z") for event in session["events"])
    assert all(
        row["created_at"].endswith("Z") for row in client.get("/api/library").json()["documents"]
    )
