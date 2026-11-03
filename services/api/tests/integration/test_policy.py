"""Policy authority is an explicit, immutable human attestation, never a proposal side effect."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError


def start(client: TestClient, scenario: str = "night-market", version: str | None = None) -> dict:
    response = client.post(
        "/api/sessions",
        json={
            "scenario_id": scenario,
            "allow_draft_rehearsal": True,
            "playbook_version_id": version,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def gap(client: TestClient) -> dict:
    session = start(client)
    response = client.post(
        f"/api/sessions/{session['id']}/choose",
        json={"choice_id": "escalate", "expected_revision": 0},
    )
    assert response.status_code == 200
    return response.json()


def proposed(client: TestClient, parent: dict) -> dict:
    choices = deepcopy(
        next(
            node
            for node in parent["result"]["input_snapshot"]["graph"]["nodes"]
            if node["id"] == "weather"
        )["choices"]
    )
    choices.append(
        {
            "id": "shelter",
            "label": "Pause admission and contact the venue manager",
            "destination": "end",
            "conditions": [
                {"field": "rain_risk", "operator": "gt", "value": 70},
                {"field": "indoor_spaces", "operator": "lte", "value": 0},
            ],
            "source_refs": choices[0]["source_refs"],
            "evidence_status": "cited",
        }
    )
    response = client.post(
        f"/api/sessions/{parent['id']}/proposals",
        json={
            "expected_revision": parent["revision"],
            "rationale": "Model a capacity-exhausted response",
            "choices": choices,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def approval(version: dict) -> dict:
    return {
        "expected_graph_hash": version["graph_hash"],
        "reviewer": "Local test reviewer",
        "notes": "Explicit source review test; no production authority implied",
        "confirmed_source_support": True,
        "reviewed_choices": [
            {"node_id": node["id"], "choice_id": choice["id"]}
            for node in version["graph"]["nodes"]
            for choice in node["choices"]
        ],
    }


def test_proposed_policy_rehearsal_completes_without_promoting_or_mutating_parent(
    client: TestClient,
) -> None:
    parent = gap(client)
    proposal = proposed(client, parent)
    assert proposal["review_status"] == "pending" and proposal["evidence_status"] == "uncited"
    assert proposal["choices"][-1]["source_refs"] == []  # Forged citation inheritance is stripped.
    assert proposal["choices"][-1]["evidence_status"] == "uncited"
    assert client.get(f"/api/proposals/{proposal['id']}").json() == proposal
    version_id = proposal["proposed_playbook_version_id"]
    version = client.get(f"/api/playbooks/{version_id}").json()
    assert version["status"] == "draft" and version["parent_version_id"] == "night-market-v1"
    assert (
        client.post(f"/api/playbooks/{version_id}/approve", json=approval(version)).status_code
        == 422
    )
    assert client.post(f"/api/proposals/{proposal['id']}/rehearse", json={}).status_code == 422
    response = client.post(
        f"/api/proposals/{proposal['id']}/rehearse", json={"allow_draft_rehearsal": True}
    )
    assert response.status_code == 201, response.text
    alternate = response.json()
    assert alternate["status"] == "awaiting_decision"
    assert alternate["proposal_id"] == proposal["id"]
    assert alternate["result"]["decisions_made"] == parent["result"]["decisions_made"]
    assert alternate["events"][0]["context_hash"] != parent["events"][0]["context_hash"]
    completed = client.post(
        f"/api/sessions/{alternate['id']}/choose",
        json={"choice_id": "shelter", "expected_revision": 0},
    ).json()
    assert completed["status"] == "completed"
    assert client.get(f"/api/sessions/{parent['id']}").json() == parent
    assert client.get(f"/api/sessions/{completed['id']}/replay").json()["verified"] is True
    params = {"left_id": parent["id"], "right_id": completed["id"]}
    assert client.get("/api/sessions/compare", params=params).status_code == 422
    comparison = client.get(
        "/api/sessions/compare", params={**params, "allow_policy_change": True}
    ).json()
    assert comparison["scope"] == "proposed_policy" and comparison["shared_event_prefix"] is None
    assert comparison["left"]["uncovered_count"] == 1
    assert comparison["right"]["uncovered_count"] == 0
    assert comparison["right"]["reviewed_supported_count"] == 0
    assert comparison["right"]["proposals"][0]["review_status"] == "pending"
    assert comparison["right"]["decisions"][-1]["evidence_status"] == "uncited"
    assert client.get(f"/api/playbooks/{version_id}").json()["status"] == "draft"


def test_proposals_require_real_blocked_checkpoint_change_and_valid_graph(
    client: TestClient,
) -> None:
    waiting = start(client)
    payload = {
        "expected_revision": 0,
        "rationale": "review",
        "choices": waiting["result"]["input_snapshot"]["graph"]["nodes"][1]["choices"],
    }
    assert client.post(f"/api/sessions/{waiting['id']}/proposals", json=payload).status_code == 409
    parent = gap(client)
    choices = next(
        node["choices"]
        for node in parent["result"]["input_snapshot"]["graph"]["nodes"]
        if node["id"] == "weather"
    )
    payload.update(expected_revision=parent["revision"], choices=deepcopy(choices))
    assert client.post(f"/api/sessions/{parent['id']}/proposals", json=payload).status_code == 422
    payload["choices"][0]["destination"] = "missing"
    assert client.post(f"/api/sessions/{parent['id']}/proposals", json=payload).status_code == 422
    payload["expected_revision"] = 0
    assert client.post(f"/api/sessions/{parent['id']}/proposals", json=payload).status_code == 409
    assert client.get(f"/api/sessions/{parent['id']}").json() == parent


def test_same_engine_resolves_a_support_overlap_only_under_an_unapproved_proposal(
    client: TestClient,
) -> None:
    parent = start(client, "customer-support")
    graph = parent["result"]["input_snapshot"]["graph"]
    choices = deepcopy(next(node["choices"] for node in graph["nodes"] if node["id"] == "refund"))
    choices[0]["conditions"].append(
        {"field": "promotional_purchase", "operator": "eq", "value": False}
    )
    response = client.post(
        f"/api/sessions/{parent['id']}/proposals",
        json={
            "expected_revision": 0,
            "rationale": "Explicitly exclude promotions from the standard branch",
            "choices": choices,
        },
    )
    assert response.status_code == 201, response.text
    proposal = response.json()
    alternate = client.post(
        f"/api/proposals/{proposal['id']}/rehearse", json={"allow_draft_rehearsal": True}
    ).json()
    assert alternate["status"] == "awaiting_decision"
    assert len(alternate["result"]["checkpoint"]["matching_choice_ids"]) == 1
    assert alternate["result"]["playbook_authority"] == "draft"
    assert client.get(f"/api/sessions/{parent['id']}").json() == parent


def test_review_requires_current_hash_all_choices_and_explicit_confirmation(
    client: TestClient,
) -> None:
    version = client.get("/api/playbooks/night-market-v1").json()
    assert client.get("/api/playbooks/night-market-v1/review").json() is None
    for patch in (
        {"expected_graph_hash": "0" * 64},
        {"reviewed_choices": []},
        {"confirmed_source_support": False},
        {"reviewer": "  "},
        {"reviewed_choices": approval(version)["reviewed_choices"] * 2},
    ):
        response = client.post(
            "/api/playbooks/night-market-v1/approve", json={**approval(version), **patch}
        )
        assert response.status_code in {409, 422}, response.text
    assert client.get("/api/playbooks/night-market-v1").json()["status"] == "draft"


def test_approval_records_review_but_never_rewrites_old_run_authority(
    client: TestClient, database: Engine
) -> None:
    old = gap(client)
    version = client.get("/api/playbooks/night-market-v1").json()
    response = client.post("/api/playbooks/night-market-v1/approve", json=approval(version))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"
    audit = client.get("/api/playbooks/night-market-v1/review").json()
    assert (
        audit["graph_hash"] == version["graph_hash"] and audit["reviewer"] == "Local test reviewer"
    )
    assert (
        client.post("/api/playbooks/night-market-v1/approve", json=approval(version)).status_code
        == 409
    )
    assert client.get(f"/api/sessions/{old['id']}").json() == old
    assert client.get(f"/api/sessions/{old['id']}/report").json()["playbook_authority"] == "draft"
    new = start(client)
    assert new["result"]["playbook_authority"] == "approved"
    for statement in (
        "UPDATE playbook_reviews SET reviewer = 'tampered'",
        "DELETE FROM playbook_reviews",
        "UPDATE playbook_versions SET graph_json = '{}' WHERE id='night-market-v1'",
    ):
        with pytest.raises(IntegrityError), database.begin() as connection:
            connection.execute(text(statement))


def test_revisions_can_use_new_immutable_source_and_reject_foreign_citations(
    client: TestClient,
) -> None:
    version = client.get("/api/playbooks/night-market-v1").json()
    source = client.post(
        "/api/documents",
        json={"title": "Revised fictional procedure", "content": "New reviewed fictional source"},
    ).json()
    payload = {
        "title": version["title"],
        "document_id": source["id"],
        "graph": deepcopy(version["graph"]),
    }
    assert client.post("/api/playbooks/night-market-v1/revisions", json=payload).status_code == 422
    for node in payload["graph"]["nodes"]:
        node["source_refs"] = []
        for choice in node["choices"]:
            choice["source_refs"] = [source["segments"][0]["id"]]
    response = client.post("/api/playbooks/night-market-v1/revisions", json=payload)
    assert response.status_code == 201, response.text
    revision = response.json()
    assert revision["status"] == "draft" and revision["parent_version_id"] == version["id"]
    assert client.get("/api/playbooks/night-market-v1").json() == version
    session = start(client, version=revision["id"])
    assert session["document_id"] == source["id"]
    assert (
        client.post(
            "/api/sessions",
            json={
                "scenario_id": "customer-support",
                "playbook_version_id": revision["id"],
                "allow_draft_rehearsal": True,
            },
        ).status_code
        == 422
    )
    assert (
        client.post(f"/api/playbooks/{revision['id']}/approve", json=approval(revision)).status_code
        == 200
    )


def test_immutable_proposal_and_changed_draft_cannot_silently_rewrite_proposal_rehearsal(
    client: TestClient, database: Engine
) -> None:
    parent = gap(client)
    proposal = proposed(client, parent)
    for statement in (
        "UPDATE rule_proposals SET review_status = 'approved'",
        "DELETE FROM rule_proposals",
    ):
        with pytest.raises(IntegrityError), database.begin() as connection:
            connection.execute(text(statement))
    with database.begin() as connection:
        connection.execute(
            text("UPDATE playbook_versions SET graph_json = '{}' WHERE id=:id"),
            {"id": proposal["proposed_playbook_version_id"]},
        )
    response = client.post(
        f"/api/proposals/{proposal['id']}/rehearse", json={"allow_draft_rehearsal": True}
    )
    assert response.status_code == 409
    assert client.get(f"/api/proposals/{proposal['id']}").json() == proposal


def test_imported_source_gets_a_real_empty_draft_and_cannot_be_approved_without_rules(
    client: TestClient,
) -> None:
    source = client.post(
        "/api/documents", json={"title": "Fictional import", "content": "Check the vendor delay."}
    ).json()
    response = client.post(f"/api/documents/{source['id']}/draft", json={"title": source["title"]})
    assert response.status_code == 201, response.text
    draft = response.json()
    assert client.get(f"/api/playbooks/{draft['id']}").json() == draft
    assert draft["graph"]["nodes"][0]["next_node"] == "end"
    assert (
        client.post(f"/api/playbooks/{draft['id']}/approve", json=approval(draft)).status_code
        == 422
    )
    assert client.post("/api/documents/missing/draft", json={"title": "Missing"}).status_code == 404


def test_compatible_scenarios_follow_version_lineage_and_never_guess_a_domain(
    client: TestClient,
) -> None:
    assert [
        scenario["id"] for scenario in client.get("/api/playbooks/night-market-v1/scenarios").json()
    ] == ["night-market"]
    parent = gap(client)
    proposal = proposed(client, parent)
    assert [
        scenario["id"]
        for scenario in client.get(
            f"/api/playbooks/{proposal['proposed_playbook_version_id']}/scenarios"
        ).json()
    ] == ["night-market"]
    original = client.get("/api/playbooks/night-market-v1").json()
    unrelated = client.post(
        "/api/playbooks",
        json={
            "document_id": original["document_id"],
            "title": "Independent model",
            "graph": original["graph"],
        },
    ).json()
    assert client.get(f"/api/playbooks/{unrelated['id']}/scenarios").json() == []
