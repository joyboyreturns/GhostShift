from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Condition(StrictModel):
    field: str = Field(min_length=1, max_length=100)
    operator: Literal["eq", "neq", "gt", "gte", "lt", "lte", "in"]
    value: str | int | float | bool | list[str | int | float | bool]

    @model_validator(mode="after")
    def valid_operand(self) -> Self:
        if self.operator == "in" and not isinstance(self.value, list):
            raise ValueError("in requires a list operand")
        if self.operator in {"gt", "gte", "lt", "lte"} and (
            isinstance(self.value, bool) or not isinstance(self.value, (int, float))
        ):
            raise ValueError("ordered comparisons require numeric operands")
        return self


class Choice(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=300)
    destination: str
    conditions: list[Condition] = Field(min_length=1, max_length=20)
    source_refs: list[str] = Field(default_factory=list, max_length=50)
    evidence_status: Literal["cited", "uncited"]

    @model_validator(mode="after")
    def evidence_consistent(self) -> Self:
        if (self.evidence_status == "cited") != bool(self.source_refs):
            raise ValueError("cited evidence requires references; uncited evidence has none")
        return self


class Node(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=300)
    type: Literal["start", "decision", "action", "end"]
    source_refs: list[str] = Field(default_factory=list, max_length=50)
    choices: list[Choice] = Field(default_factory=list, max_length=50)
    next_node: str | None = None

    @model_validator(mode="after")
    def transitions(self) -> Self:
        if self.type == "decision":
            if not self.choices or self.next_node is not None:
                raise ValueError("decisions require choices and no next_node")
        elif self.choices:
            raise ValueError("only decisions can contain choices")
        if self.type in {"start", "action"} and not self.next_node:
            raise ValueError("start/action nodes require next_node")
        if self.type == "end" and self.next_node:
            raise ValueError("end nodes cannot have transitions")
        if len({c.id for c in self.choices}) != len(self.choices):
            raise ValueError("choice IDs must be unique within a node")
        return self


class Graph(StrictModel):
    nodes: list[Node] = Field(min_length=2, max_length=200)

    @model_validator(mode="after")
    def topology(self) -> Self:
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("node IDs must be unique")
        starts = [n for n in self.nodes if n.type == "start"]
        if len(starts) != 1 or not any(n.type == "end" for n in self.nodes):
            raise ValueError("graph needs exactly one start and at least one end")
        adjacency = {
            n.id: ([n.next_node] if n.next_node else []) + [c.destination for c in n.choices]
            for n in self.nodes
        }
        if any(d not in ids for destinations in adjacency.values() for d in destinations):
            raise ValueError("transition points to nonexistent node")
        reached: set[str] = set()
        pending = [starts[0].id]
        while pending:
            current = pending.pop()
            if current not in reached:
                reached.add(current)
                pending.extend(adjacency[current])
        if reached != ids:
            raise ValueError("all nodes must be reachable from start")
        # Cycles are permitted: termination semantics belong to the future engine.
        return self

    def validate_references(self, segment_ids: set[str]) -> None:
        for node in self.nodes:
            refs = node.source_refs + [r for c in node.choices for r in c.source_refs]
            if not set(refs).issubset(segment_ids):
                raise ValueError(f"invalid source reference in node {node.id}")
