"""Immutable proposal snapshots, explicit human review and version lineage."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite permits a nullable REFERENCES column without rebuilding immutable rows.
    op.execute(
        "ALTER TABLE playbook_versions ADD COLUMN parent_version_id VARCHAR "
        "REFERENCES playbook_versions(id)"
    )
    op.create_table(
        "playbook_reviews",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "playbook_version_id",
            sa.String(),
            sa.ForeignKey("playbook_versions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("graph_hash", sa.String(), nullable=False),
        sa.Column("reviewer", sa.String(), nullable=False),
        sa.Column("notes", sa.String(), nullable=False),
        sa.Column("reviewed_choices_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "rule_proposals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "session_id", sa.String(), sa.ForeignKey("simulation_sessions.id"), nullable=False
        ),
        sa.Column(
            "playbook_version_id",
            sa.String(),
            sa.ForeignKey("playbook_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "proposed_playbook_version_id",
            sa.String(),
            sa.ForeignKey("playbook_versions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("target_node_id", sa.String(), nullable=False),
        sa.Column("rationale", sa.String(), nullable=False),
        sa.Column("proposed_change_json", sa.JSON(), nullable=False),
        sa.Column("evidence_status", sa.String(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for table in ("playbook_reviews", "rule_proposals"):
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} "
                f"ON {table} BEGIN SELECT RAISE(ABORT, 'immutable review/proposal'); END"
            )


def downgrade() -> None:
    op.drop_table("rule_proposals")
    op.drop_table("playbook_reviews")
    op.execute("ALTER TABLE playbook_versions DROP COLUMN parent_version_id")
