import copy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.entities import Base, Document, PlaybookVersion
from app.schemas.api import DocumentInput
from app.schemas.graph import Graph
from app.services.documents import create_document, segment_document
from app.services.seed import FIXTURES


def test_health_and_catalog(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok", "milestone": 6}
    entries = client.get("/api/demo").json()["demos"]
    assert len(entries) == 2
    assert all(entry["fictional"] and entry["scenario_status"] == "ready" for entry in entries)


@pytest.mark.parametrize("source_type", ["text", "markdown"])
def test_import_roundtrip(client: TestClient, source_type: str) -> None:
    text = "  First paragraph.\r\n\r\nSecond 🌧 paragraph.\n\nThird.  "
    response = client.post(
        "/api/documents",
        json={
            "title": "Test procedure",
            "content": text,
            "source_type": source_type,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == text
    assert len(data["segments"]) == 3
    for segment in data["segments"]:
        assert text[segment["start_offset"] : segment["end_offset"]] == segment["text"]
    assert client.get("/api/documents/" + data["id"]).json() == data
    repeated = segment_document(data["id"], text)
    assert [s.id for s in repeated] == [s["id"] for s in data["segments"]]


def test_import_limits_and_errors(client: TestClient) -> None:
    for content in [" \n", "x" * 100001]:
        response = client.post("/api/documents", json={"title": "Test", "content": content})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
    assert client.get("/api/documents/missing").status_code == 404
    assert client.post("/api/sessions").status_code == 415


def test_fixture_integrity(client: TestClient) -> None:
    for entry in client.get("/api/demo").json()["demos"]:
        document = client.get("/api/documents/" + entry["document_id"]).json()
        playbook = client.get("/api/playbooks/" + entry["playbook_id"]).json()
        graph = Graph.model_validate(playbook["graph"])
        graph.validate_references({s["id"] for s in document["segments"]})
        assert playbook["status"] == "draft"
        assert "FICTIONAL" in document["content"]
        assert (FIXTURES / entry["id"] / "scenario.json").is_file()


def test_graph_rejects_invalid_destinations_and_sources(client: TestClient) -> None:
    playbook = client.get("/api/playbooks/night-market-v1").json()
    graph = copy.deepcopy(playbook["graph"])
    graph["nodes"][0]["next_node"] = "does-not-exist"
    with pytest.raises(ValidationError, match="nonexistent"):
        Graph.model_validate(graph)
    graph = copy.deepcopy(playbook["graph"])
    graph["nodes"][1]["source_refs"] = ["customer-support:s1:wrong-document"]
    response = client.post(
        "/api/playbooks",
        json={
            "document_id": "night-market",
            "title": "Invalid",
            "graph": graph,
        },
    )
    assert response.status_code == 422
    assert "invalid source reference" in response.json()["error"]["message"]


def test_graph_schema_rejects_malformed_topology(client: TestClient) -> None:
    graph = client.get("/api/playbooks/night-market-v1").json()["graph"]
    duplicate = copy.deepcopy(graph)
    duplicate["nodes"][1]["id"] = "start"
    with pytest.raises(ValidationError, match="unique"):
        Graph.model_validate(duplicate)
    invalid_operand = copy.deepcopy(graph)
    invalid_operand["nodes"][1]["choices"][0]["conditions"][0]["value"] = "thirty"
    with pytest.raises(ValidationError, match="numeric"):
        Graph.model_validate(invalid_operand)


def test_create_real_draft(client: TestClient) -> None:
    source = client.get("/api/playbooks/customer-support-v1").json()
    response = client.post(
        "/api/playbooks",
        json={
            "document_id": source["document_id"],
            "title": "A new draft",
            "graph": source["graph"],
        },
    )
    assert response.status_code == 201
    new = response.json()
    assert new["version"] == 2 and new["status"] == "draft"
    assert client.get("/api/playbooks/" + new["id"]).json() == new
    assert client.get("/api/playbooks/customer-support-v1").json() == source


def test_orm_immutability() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        document = create_document(db, DocumentInput(title="Original", content="Original"))
        db.commit()
        document.content = "tampered"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()
        stored = db.scalar(select(Document))
        assert stored and stored.content == "Original"
        playbook = PlaybookVersion(
            document_id=stored.id,
            version=1,
            title="Reviewed",
            status="approved",
            graph_json={"nodes": []},
        )
        db.add(playbook)
        db.commit()
        playbook.title = "tampered"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()
    engine.dispose()
