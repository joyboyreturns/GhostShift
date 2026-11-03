"""Preserve PDF file identity and extracted-page provenance without changing existing sources."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents ADD COLUMN original_file_hash VARCHAR")
    op.execute("ALTER TABLE documents ADD COLUMN page_count INTEGER")
    op.execute("ALTER TABLE documents ADD COLUMN empty_pages_json JSON")
    op.execute("ALTER TABLE source_segments ADD COLUMN page_number INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE source_segments DROP COLUMN page_number")
    op.execute("ALTER TABLE documents DROP COLUMN empty_pages_json")
    op.execute("ALTER TABLE documents DROP COLUMN page_count")
    op.execute("ALTER TABLE documents DROP COLUMN original_file_hash")
