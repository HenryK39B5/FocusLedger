from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_add_source_groups_and_tags"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("article_sources", sa.Column("source_group", sa.String(length=255), nullable=True))
    op.add_column("article_sources", sa.Column("tags", sa.JSON(), nullable=True, server_default=sa.text("'[]'")))
    op.execute("UPDATE article_sources SET tags = '[]' WHERE tags IS NULL")
    op.alter_column("article_sources", "tags", nullable=False, server_default=sa.text("'[]'"))
    op.create_index("ix_article_sources_source_group", "article_sources", ["source_group"])


def downgrade() -> None:
    op.drop_index("ix_article_sources_source_group", table_name="article_sources")
    op.drop_column("article_sources", "tags")
    op.drop_column("article_sources", "source_group")
