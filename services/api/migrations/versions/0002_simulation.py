"""Persist pinned simulations, immutable scenarios and append-only event history."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "playbook_version_id",
            sa.String(),
            sa.ForeignKey("playbook_versions.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("initial_facts_json", sa.JSON(), nullable=False),
        sa.Column("injects_json", sa.JSON(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("fictional", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "simulation_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scenario_id", sa.String(), sa.ForeignKey("scenarios.id"), nullable=False),
        sa.Column(
            "playbook_version_id",
            sa.String(),
            sa.ForeignKey("playbook_versions.id"),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("parent_session_id", sa.String(), sa.ForeignKey("simulation_sessions.id")),
        sa.Column("fork_event_index", sa.Integer()),
        sa.Column("engine_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("current_node_id", sa.String(), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("revision >= 0"),
    )
    op.create_table(
        "session_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "session_id", sa.String(), sa.ForeignKey("simulation_sessions.id"), nullable=False
        ),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("state_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("session_id", "sequence_number"),
        sa.CheckConstraint("sequence_number >= 0"),
    )
    op.create_index("ix_session_events_session_id", "session_events", ["session_id"])
    for table in ("scenarios", "session_events"):
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} "
                f"ON {table} BEGIN SELECT RAISE(ABORT, 'immutable scenario/event'); END"
            )
    fields = (
        "id",
        "scenario_id",
        "playbook_version_id",
        "document_id",
        "parent_session_id",
        "fork_event_index",
        "engine_version",
        "created_at",
    )
    changed = " OR ".join(f"NEW.{field} IS NOT OLD.{field}" for field in fields)
    op.execute(
        "CREATE TRIGGER pinned_session_identity BEFORE UPDATE ON simulation_sessions "
        f"WHEN {changed} BEGIN SELECT RAISE(ABORT, 'immutable session identity'); END"
    )


def downgrade() -> None:
    op.drop_table("session_events")
    op.drop_table("simulation_sessions")
    op.drop_table("scenarios")
