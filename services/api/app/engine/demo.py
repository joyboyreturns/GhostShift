"""Codex integration harness for the Kiro-authored engine and fictional fixtures.

This is a local, explicitly unapproved batch rehearsal; it is not a report/session API.
"""

import json
from copy import deepcopy
from pathlib import Path

from app.engine.interfaces import Inject, RunInput, Scenario
from app.engine.interpreter import GhostShiftEngine
from app.schemas.graph import Graph
from app.services.segmentation import segment_document

FIXTURES = Path(__file__).resolve().parents[4] / "fixtures"


def fixture_input(name: str) -> RunInput:
    folder = FIXTURES / name
    fixture = json.loads((folder / "fixture.json").read_text())
    scenario_data = json.loads((folder / "scenario.json").read_text())
    if fixture.get("fictional") is not True or scenario_data.get("fictional") is not True:
        raise ValueError("The demo harness accepts only explicitly fictional fixtures")
    segments = segment_document(name, (folder / "runbook.md").read_text())
    references = {segment.ordinal: segment.id for segment in segments}
    data = deepcopy(fixture["graph"])
    for node in data["nodes"]:
        node["source_refs"] = [references[index] for index in node["source_refs"]]
        for choice in node.get("choices", []):
            choice["source_refs"] = [references[index] for index in choice["source_refs"]]
    graph = Graph.model_validate(data)
    graph.validate_references(set(references.values()))
    return RunInput(
        playbook_version_id=f"{name}-v1",
        playbook_authority="draft",
        execution_mode="auto_rehearsal",
        graph=graph,
        scenario=Scenario(
            title=scenario_data["title"],
            seed=scenario_data["seed"],
            initial_facts=scenario_data["initial_facts"],
            injects=[Inject.model_validate(inject) for inject in scenario_data["injects"]],
        ),
    )


def main() -> None:
    summaries = []
    for name in ("night-market", "customer-support"):
        result = GhostShiftEngine().run(fixture_input(name))
        summaries.append(
            {
                "fixture": name,
                "status": result.status,
                "stop_node": result.checkpoint.node_id if result.checkpoint else None,
                "matching_choices": result.checkpoint.matching_choice_ids
                if result.checkpoint
                else [],
                "playbook_authority": result.playbook_authority,
                "execution_mode": result.input_snapshot.execution_mode,
                "logical_event_count": len(result.events),
                "last_state_hash": result.events[-1].state_hash,
                "notice": result.rehearsal_notice,
            }
        )
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
