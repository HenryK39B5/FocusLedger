"""add notebooks

Revision ID: 0006_notebooks
Revises: 0005_article_management_fields
Create Date: 2026-04-02 13:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_notebooks"
down_revision = "0005_article_management_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notebooks",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=False, server_default="📒"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notebooks_name"), "notebooks", ["name"], unique=False)

    op.create_table(
        "notebook_articles",
        sa.Column("notebook_id", sa.String(length=32), nullable=False),
        sa.Column("article_id", sa.String(length=32), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notebook_id", "article_id", name="uq_notebook_article_pair"),
    )
    op.create_index(op.f("ix_notebook_articles_article_id"), "notebook_articles", ["article_id"], unique=False)
    op.create_index(op.f("ix_notebook_articles_notebook_id"), "notebook_articles", ["notebook_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notebook_articles_notebook_id"), table_name="notebook_articles")
    op.drop_index(op.f("ix_notebook_articles_article_id"), table_name="notebook_articles")
    op.drop_table("notebook_articles")

    op.drop_index(op.f("ix_notebooks_name"), table_name="notebooks")
    op.drop_table("notebooks")
