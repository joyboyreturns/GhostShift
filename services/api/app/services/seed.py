import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import engine
from app.engine.interfaces import Scenario as EngineScenario
from app.models.entities import Document, PlaybookVersion, Scenario
from app.schemas.api import DemoCatalog, DemoEntry, DocumentInput, PlaybookInput
from app.schemas.graph import Graph
from app.services.documents import create_document, document_output
from app.services.playbooks import create_playbook

FIXTURES = Path(__file__).resolve().parents[4] / "fixtures"


def catalog() -> DemoCatalog:
    entries = []
    for name in ["night-market", "customer-support"]:
        fixture = json.loads((FIXTURES / name / "fixture.json").read_text())
        entries.append(
            DemoEntry(
                id=name,
                title=fixture["title"],
                description=fixture["description"],
                document_id=name,
                playbook_id=name + "-v1",
                scenario_id=name,
            )
        )
    return DemoCatalog(demos=entries)


def seed(db: Session) -> DemoCatalog:
    entries = []
    for name in ["night-market", "customer-support"]:
        fixture = json.loads((FIXTURES / name / "fixture.json").read_text())
        document = db.get(Document, name)
        if document is None:
            document = create_document(
                db,
                DocumentInput(
                    title=fixture["title"],
                    content=(FIXTURES / name / "runbook.md").read_text(),
                ),
                document_id=name,
            )
        segments = document_output(db, document).segments
        graph_data = json.loads(json.dumps(fixture["graph"]))
        for node in graph_data["nodes"]:
            node["source_refs"] = [segments[i - 1].id for i in node.get("source_refs", [])]
            for choice in node.get("choices", []):
                choice["source_refs"] = [segments[i - 1].id for i in choice["source_refs"]]
        playbook_id = name + "-v1"
        if db.get(PlaybookVersion, playbook_id) is None:
            playbook = create_playbook(
                db,
                PlaybookInput(
                    document_id=document.id,
                    title=fixture["title"],
                    graph=Graph.model_validate(graph_data),
                ),
            )
            playbook.id = playbook_id
        db.flush()
        if db.get(Scenario, name) is None:
            scenario_data = json.loads((FIXTURES / name / "scenario.json").read_text())
            scenario = EngineScenario.model_validate(
                {
                    key: scenario_data[key]
                    for key in (
                        "title",
                        "seed",
                        "initial_facts",
                        "injects",
                    )
                }
            )
            nodes = {node["id"] for node in graph_data["nodes"]}
            if any(inject.before_node_id not in nodes for inject in scenario.injects):
                raise ValueError("Fixture inject references an absent node")
            db.add(
                Scenario(
                    id=name,
                    playbook_version_id=playbook_id,
                    title=scenario.title,
                    description=fixture["description"],
                    initial_facts_json=scenario.initial_facts,
                    injects_json=[inject.model_dump(mode="json") for inject in scenario.injects],
                    seed=scenario.seed,
                    fictional=True,
                )
            )
        entries.append(
            DemoEntry(
                id=name,
                title=fixture["title"],
                description=fixture["description"],
                document_id=document.id,
                playbook_id=playbook_id,
                scenario_id=name,
            )
        )
    db.commit()
    return DemoCatalog(demos=entries)


if __name__ == "__main__":
    with Session(engine) as session:
        print(seed(session).model_dump_json(indent=2))
