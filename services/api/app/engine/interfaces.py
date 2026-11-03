"""Simulation engine type contracts and Protocol.

Kiro-authored in session 2026-11-03. The original Codex-authored placeholder defined a
single-method Protocol (evaluate); that contract was too narrow to express traversal,
injects, deviations, and deterministic hashing. This module replaces it with typed input/
output contracts aligned to requirements.md and design.md in .kiro/specs/simulation-engine/.

Codex review corrections add explicit decision checkpoints, finite strict facts, self-contained
run snapshots, and authority/context on every hashed event. See docs/ENGINE_REVIEW.md.

The old `Evaluation` model and `SimulationEngine.evaluate()` signature are superseded.
No external code referenced them at the time of this implementation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from app.schemas.graph import Graph

# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

# A fact value is a scalar — never a list. Lists appear only as `in` operands
# in Condition.value, not as stored facts.
FactValue = str | int | float | bool
Facts = dict[str, FactValue]
ConditionValue = FactValue | list[FactValue]


class EngineModel(BaseModel):
    """Frozen typed contracts; the interpreter owns deep copies of nested data."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", allow_inf_nan=False)


# ---------------------------------------------------------------------------
# Engine exceptions
# ---------------------------------------------------------------------------


class EngineError(Exception):
    """Base class for engine errors."""


class TraversalBudgetExceeded(EngineError):
    """Raised when the traversal step count exceeds the configured budget.

    Prevents infinite loops on cyclic graphs.
    """

    def __init__(self, message: str, partial_result: RunResult | None = None) -> None:
        super().__init__(message)
        self.partial_result = partial_result


class InvalidScenario(EngineError):
    """Raised during pre-flight validation when the scenario is structurally invalid.

    Examples: an inject references a node ID that does not exist in the graph.
    """


class InvalidDecision(EngineError):
    """The caller supplied an unknown, out-of-order, or unused decision."""


# ---------------------------------------------------------------------------
# Scenario input
# ---------------------------------------------------------------------------


class Inject(EngineModel):
    """A mid-run fact update applied exactly once, immediately before a named node."""

    before_node_id: str
    facts: dict[str, FactValue]


class Scenario(EngineModel):
    """Immutable scenario input for one engine run."""

    title: str
    seed: int = 0
    initial_facts: dict[str, FactValue] = Field(default_factory=dict)
    injects: list[Inject] = Field(default_factory=list)


class Decision(EngineModel):
    """A caller-supplied choice at a decision node during traversal."""

    node_id: str = Field(min_length=1)
    selected_choice_id: str | None = Field(default=None, min_length=1)
    selection_origin: Literal["user", "automatic_rehearsal"] = "user"


PlaybookAuthority = Literal["draft", "approved"]
ExecutionMode = Literal["interactive", "auto_rehearsal"]


class RunInput(EngineModel):
    """Complete, immutable input for a single engine run."""

    playbook_version_id: str = Field(min_length=1)
    playbook_authority: PlaybookAuthority
    graph: Graph
    scenario: Scenario
    decisions: list[Decision] = Field(default_factory=list)
    execution_mode: ExecutionMode = "interactive"
    step_budget: int = Field(default=200, ge=1, le=10_000)


# ---------------------------------------------------------------------------
# Per-condition and per-choice evaluation output
# ---------------------------------------------------------------------------


class ConditionOutcome(EngineModel):
    """Result of evaluating a single Condition against the current facts."""

    field: str
    operator: str
    value: ConditionValue
    result: bool
    missing_fact: bool = False
    type_mismatch: bool = False


class ChoiceOutcome(EngineModel):
    """Result of evaluating all conditions on one Choice (AND-composed)."""

    choice_id: str
    matched: bool
    condition_outcomes: list[ConditionOutcome]
    source_refs: list[str]
    evidence_status: Literal["cited", "uncited"]


DecisionResult = Literal["exact_match", "uncovered", "overlap"]


class DecisionEvaluation(EngineModel):
    """Aggregated evaluation result for one decision node."""

    node_id: str
    result: DecisionResult
    matching_choice_ids: list[str]
    choice_outcomes: list[ChoiceOutcome]
    facts_snapshot: dict[str, FactValue]  # facts at time of evaluation
    node_source_refs: list[str]


# ---------------------------------------------------------------------------
# Deviation
# ---------------------------------------------------------------------------


class Deviation(EngineModel):
    """Records a caller-selected choice that did not match the engine evaluation."""

    node_id: str
    selected_choice_id: str
    matching_choice_ids: list[str]
    node_source_refs: list[str]
    selected_choice_source_refs: list[str]
    selected_choice_evidence_status: Literal["cited", "uncited"]


# ---------------------------------------------------------------------------
# Logical event and hash chain
# ---------------------------------------------------------------------------

EventType = Literal[
    "node_entered",
    "inject_applied",
    "decision_evaluated",
    "decision_selected",
    "deviation_recorded",
    "run_terminated",
]


class LogicalEvent(EngineModel):
    """One step in the deterministic event log.

    The state_hash is a SHA-256 over the canonical event inputs (see _compute_hash),
    excluding wall-clock timestamps and generated UUIDs so that replaying identical
    inputs produces identical hashes.
    """

    playbook_version_id: str
    playbook_authority: PlaybookAuthority
    execution_mode: ExecutionMode
    context_hash: str
    sequence: int
    event_type: EventType
    node_id: str
    payload: dict[str, JsonValue]
    facts_snapshot: dict[str, FactValue]
    state_hash: str


# ---------------------------------------------------------------------------
# Run result
# ---------------------------------------------------------------------------

RunStatus = Literal[
    "completed",
    "uncovered",
    "overlap",
    "deviation",
    "budget_exceeded",
    "awaiting_decision",
]

_REHEARSAL_NOTICE = (
    "This is a model-only rehearsal of a {authority} playbook. "
    "No result constitutes approved policy or emergency guidance. "
    "All seeded rules require human review before operational use."
)


class RunResult(EngineModel):
    """Complete, serialisable output of one engine run.

    Carries enough information for a future replay layer to reconstruct the run
    deterministically (playbook_version_id + scenario + decisions_made + events with hashes).
    """

    input_snapshot: RunInput
    playbook_version_id: str
    playbook_authority: PlaybookAuthority
    scenario_title: str
    scenario_seed: int
    status: RunStatus
    events: list[LogicalEvent]
    deviations: list[Deviation]
    final_facts: dict[str, FactValue]
    decisions_made: list[Decision]
    remaining_decisions: list[Decision]
    checkpoint: DecisionEvaluation | None = None
    rehearsal_notice: str


# ---------------------------------------------------------------------------
# Updated Protocol
# ---------------------------------------------------------------------------


class SimulationEngine(Protocol):
    def run(self, input: RunInput) -> RunResult:
        """Execute a full graph traversal and return a deterministic, immutable result.

        The engine MUST NOT mutate the input graph or facts. It MUST NOT invent
        policy responses for uncovered or overlap decisions. It MUST NOT use
        wall-clock time or OS randomness in the event hash chain.
        """
        ...


# ---------------------------------------------------------------------------
# Hash utility (used by interpreter; defined here for testability)
# ---------------------------------------------------------------------------


def _json_default(obj: object) -> object:
    """Raise on any non-serialisable type to prevent silent hash corruption."""
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


def compute_event_hash(
    playbook_version_id: str,
    sequence: int,
    node_id: str,
    event_type: str,
    payload: dict[str, JsonValue],
    facts_snapshot: dict[str, FactValue],
    prev_hash: str,
    *,
    playbook_authority: PlaybookAuthority,
    execution_mode: ExecutionMode,
    context_hash: str,
) -> str:
    """Return SHA-256 hex digest of the canonical event representation.

    Excludes wall-clock timestamps, generated UUIDs, and anything non-deterministic.
    Replaying identical inputs MUST produce identical return values.
    """
    data = {
        "playbook_version_id": playbook_version_id,
        "sequence": sequence,
        "node_id": node_id,
        "event_type": event_type,
        "payload": payload,
        "facts_snapshot": facts_snapshot,
        "prev_hash": prev_hash,
        "playbook_authority": playbook_authority,
        "execution_mode": execution_mode,
        "context_hash": context_hash,
    }
    canonical = json.dumps(
        data, sort_keys=True, separators=(",", ":"), default=_json_default, allow_nan=False
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
