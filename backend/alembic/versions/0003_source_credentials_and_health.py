from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_source_credentials"
down_revision = "0002_add_source_groups_and_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM article_embeddings")
    op.execute("DELETE FROM article_metrics")
    op.execute("DELETE FROM novelty_analyses")
    op.execute("DELETE FROM recommendation_results")
    op.execute("DELETE FROM feedback_events")
    op.execute("DELETE FROM articles")
    op.execute("DELETE FROM article_sources")

    op.alter_column("article_sources", "source_identifier", existing_type=sa.String(length=2048), nullable=True)
    op.add_column("article_sources", sa.Column("biz", sa.String(length=128), nullable=True))
    op.add_column("article_sources", sa.Column("public_home_link", sa.String(length=2048), nullable=True))
    op.add_column(
        "article_sources",
        sa.Column("credential_status", sa.String(length=32), nullable=False, server_default="unknown"),
    )
    op.add_column("article_sources", sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("article_sources", sa.Column("last_sync_succeeded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("article_sources", sa.Column("last_sync_failed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("article_sources", sa.Column("last_error_code", sa.String(length=64), nullable=True))
    op.add_column("article_sources", sa.Column("last_error_message", sa.String(length=1000), nullable=True))
    op.create_index("ix_article_sources_biz", "article_sources", ["biz"], unique=True)
    op.create_index("ix_article_sources_credential_status", "article_sources", ["credential_status"], unique=False)

    op.create_table(
        "source_credentials",
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("raw_link", sa.String(length=4096), nullable=False),
        sa.Column("token_biz", sa.String(length=128), nullable=False),
        sa.Column("uin", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=2048), nullable=False),
        sa.Column("pass_ticket", sa.String(length=4096), nullable=False),
        sa.Column("appmsg_token", sa.String(length=2048), nullable=True),
        sa.Column("session_us", sa.String(length=2048), nullable=True),
        sa.Column("scene", sa.String(length=64), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("raw_query", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_id"], ["article_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_source_credentials_source_id", "source_credentials", ["source_id"], unique=True)
    op.create_index("ix_source_credentials_token_biz", "source_credentials", ["token_biz"], unique=False)

    op.alter_column("article_sources", "biz", nullable=False)
    op.alter_column("article_sources", "public_home_link", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_source_credentials_token_biz", table_name="source_credentials")
    op.drop_index("ix_source_credentials_source_id", table_name="source_credentials")
    op.drop_table("source_credentials")

    op.drop_index("ix_article_sources_credential_status", table_name="article_sources")
    op.drop_index("ix_article_sources_biz", table_name="article_sources")
    op.drop_column("article_sources", "last_error_message")
    op.drop_column("article_sources", "last_error_code")
    op.drop_column("article_sources", "last_sync_failed_at")
    op.drop_column("article_sources", "last_sync_succeeded_at")
    op.drop_column("article_sources", "last_verified_at")
    op.drop_column("article_sources", "credential_status")
    op.drop_column("article_sources", "public_home_link")
    op.drop_column("article_sources", "biz")
    op.alter_column("article_sources", "source_identifier", existing_type=sa.String(length=2048), nullable=False)
