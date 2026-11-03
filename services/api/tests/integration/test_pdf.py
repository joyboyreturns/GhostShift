import base64
import hashlib
import subprocess

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.services import pdf_import
from tests.helpers.pdf import make_pdf


def upload(client: TestClient, content: bytes):
    return client.post(
        "/api/documents/pdf",
        json={"title": "Fictional PDF procedure", "pdf_base64": base64.b64encode(content).decode()},
    )


def test_real_pdf_extraction_preserves_file_hash_pages_offsets_and_empty_page_warning(
    client: TestClient, database: Engine
) -> None:
    content = make_pdf(
        ["Fictional café vendor policy.", None, "Escalate delays of at least 30 minutes."]
    )
    response = upload(client, content)
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["source_type"] == "pdf" and document["page_count"] == 3
    assert document["empty_pages"] == [2]
    assert document["original_file_hash"] == hashlib.sha256(content).hexdigest()
    assert document["content_hash"] == hashlib.sha256(document["content"].encode()).hexdigest()
    assert [segment["page_number"] for segment in document["segments"]] == [1, 3]
    assert "café" in document["segments"][0]["text"]
    for segment in document["segments"]:
        assert (
            document["content"][segment["start_offset"] : segment["end_offset"]] == segment["text"]
        )
    assert client.get(f"/api/documents/{document['id']}").json() == document
    for statement in (
        "UPDATE documents SET page_count=99 WHERE id=:id",
        "UPDATE source_segments SET page_number=99 WHERE document_id=:id",
    ):
        with pytest.raises(IntegrityError, match="immutable source"), database.begin() as db:
            db.execute(text(statement), {"id": document["id"]})


def test_pdf_rejects_scans_encryption_invalid_data_page_and_text_limits_without_writes(
    client: TestClient,
) -> None:
    initial = client.get("/api/library").json()["totals"]["documents"]
    for content in (
        b"not a PDF",
        b"%PDF-malformed",
        make_pdf([None]),
        make_pdf(["Fictional"], encrypted=True),
        make_pdf([None] * 21),
        make_pdf(["x" * 100001]),
    ):
        response = upload(client, content)
        assert response.status_code == 422, response.text
    assert (
        client.post("/api/documents/pdf", json={"title": "Bad", "pdf_base64": "%%%"}).status_code
        == 422
    )
    assert upload(client, b"%PDF-" + b"x" * (256 * 1024)).status_code == 422
    assert client.get("/api/library").json()["totals"]["documents"] == initial


def test_pdf_parser_timeout_releases_capacity_and_busy_slot_has_retry_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = make_pdf(["Fictional source text"])
    with monkeypatch.context() as patch:

        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired("pdf worker", 5)

        patch.setattr(pdf_import.subprocess, "run", timeout)
        response = upload(client, content)
        assert response.status_code == 422 and "time limit" in response.json()["error"]["message"]
    assert pdf_import._parser_slot.acquire(blocking=False)
    try:
        busy = upload(client, content)
        assert busy.status_code == 429 and busy.headers["retry-after"] == "5"
    finally:
        pdf_import._parser_slot.release()
    assert upload(client, content).status_code == 201


def test_pdf_page_evidence_and_original_file_identity_survive_report_export(
    client: TestClient,
) -> None:
    content = make_pdf(["A fictional preface.", "Escalate delays of at least 30 minutes."])
    document = upload(client, content).json()
    reference = document["segments"][1]["id"]
    model = client.post(
        "/api/playbooks",
        json={
            "document_id": document["id"],
            "title": "PDF model",
            "graph": {
                "nodes": [
                    {"id": "start", "label": "Begin", "type": "start", "next_node": "decision"},
                    {
                        "id": "decision",
                        "label": "Delay?",
                        "type": "decision",
                        "source_refs": [reference],
                        "choices": [
                            {
                                "id": "escalate",
                                "label": "Escalate",
                                "destination": "end",
                                "conditions": [{"field": "delay", "operator": "gte", "value": 30}],
                                "source_refs": [reference],
                                "evidence_status": "cited",
                            }
                        ],
                    },
                    {"id": "end", "label": "Done", "type": "end"},
                ]
            },
        },
    ).json()
    scenario = client.post(
        "/api/scenarios",
        json={
            "playbook_version_id": model["id"],
            "title": "Fictional PDF rehearsal",
            "initial_facts": {"delay": 45},
            "fictional": True,
        },
    ).json()
    run = client.post(
        "/api/sessions", json={"scenario_id": scenario["id"], "allow_draft_rehearsal": True}
    ).json()
    assert (
        client.post(
            f"/api/sessions/{run['id']}/choose",
            json={"choice_id": "escalate", "expected_revision": 0},
        ).status_code
        == 200
    )
    report = client.get(f"/api/sessions/{run['id']}/report").json()
    assert report["original_file_hash"] == document["original_file_hash"]
    assert report["evidence"][0]["page_number"] == 2
    assert report["evidence"][0]["text"] == document["segments"][1]["text"]
