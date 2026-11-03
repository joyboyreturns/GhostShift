import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.graph import Graph
from app.services.segmentation import segment_document

FIXTURES = Path(__file__).resolve().parents[4] / "fixtures"


@pytest.mark.parametrize("name", ["night-market", "customer-support"])
def test_fixture_evidence_and_topology(name: str) -> None:
    content = (FIXTURES / name / "runbook.md").read_text()
    segments = segment_document(name, content)
    data = json.loads((FIXTURES / name / "fixture.json").read_text())
    for node in data["graph"]["nodes"]:
        node["source_refs"] = [segments[i - 1].id for i in node["source_refs"]]
        for choice in node.get("choices", []):
            choice["source_refs"] = [segments[i - 1].id for i in choice["source_refs"]]
    graph = Graph.model_validate(data["graph"])
    graph.validate_references({s.id for s in segments})
    assert "FICTIONAL" in content
    with pytest.raises(ValueError, match="invalid source reference"):
        graph.validate_references(set())
    if name == "night-market":
        weather = next(n for n in graph.nodes if n.id == "weather")
        assert "Weather" in next(s.text for s in segments if s.id == weather.source_refs[0])
    data["graph"]["nodes"][0]["next_node"] = "absent"
    with pytest.raises(ValidationError, match="nonexistent"):
        Graph.model_validate(data["graph"])


@pytest.mark.parametrize(
    "content",
    [
        "One.\n\nTwo.",
        "  One.\r\n\r\nTwo 🌧.  ",
        "\n\n",
        "Single",
        "A\nB\n\nC",
    ],
)
def test_segmentation_offsets_and_identity(content: str) -> None:
    first = segment_document("document", content)
    assert first == segment_document("document", content)
    assert len({s.id for s in first}) == len(first)
    for segment in first:
        assert content[segment.start_offset : segment.end_offset] == segment.text
        assert segment.text.strip()
        assert segment.id not in {s.id for s in segment_document("other", content)}
