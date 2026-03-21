from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_sources",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_identifier", sa.String(2048), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.String(1000)),
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("preferred_topics", sa.JSON(), nullable=False),
        sa.Column("disliked_topics", sa.JSON(), nullable=False),
        sa.Column("preferred_content_types", sa.JSON(), nullable=False),
        sa.Column("preferred_styles", sa.JSON(), nullable=False),
        sa.Column("followed_topics", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", sa.String(32), sa.ForeignKey("article_sources.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author", sa.String(255)),
        sa.Column("publish_time", sa.String(64)),
        sa.Column("url", sa.String(2048), nullable=False, unique=True),
        sa.Column("raw_html_path", sa.String(1024)),
        sa.Column("raw_text", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("topic_tags", sa.JSON(), nullable=False),
        sa.Column("entity_tags", sa.JSON(), nullable=False),
        sa.Column("content_type", sa.String(64)),
        sa.Column("core_claims", sa.JSON(), nullable=False),
        sa.Column("key_variables", sa.JSON(), nullable=False),
        sa.Column("catalysts", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("style_tags", sa.JSON(), nullable=False),
        sa.Column("recommendation_reason", sa.Text()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )

    op.create_index("ix_articles_source_id", "articles", ["source_id"])
    op.create_index("ix_articles_publish_time", "articles", ["publish_time"])
    op.create_index("ix_articles_title", "articles", ["title"])

    op.create_table(
        "article_metrics",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("article_id", sa.String(32), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("read_count", sa.Integer()),
        sa.Column("like_count", sa.Integer()),
        sa.Column("repost_count", sa.Integer()),
        sa.Column("comment_count", sa.Integer()),
        sa.Column("comment_like_count", sa.Integer()),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_article_metrics_article_id", "article_metrics", ["article_id"])

    op.create_table(
        "novelty_analyses",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("article_id", sa.String(32), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("compared_article_ids", sa.JSON(), nullable=False),
        sa.Column("repeated_points", sa.JSON(), nullable=False),
        sa.Column("incremental_points", sa.JSON(), nullable=False),
        sa.Column("novelty_type_breakdown", sa.JSON(), nullable=False),
        sa.Column("novelty_score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text()),
    )
    op.create_index("ix_novelty_analyses_article_id", "novelty_analyses", ["article_id"])

    op.create_table(
        "feedback_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("article_id", sa.String(32), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("feedback_type", sa.String(64), nullable=False),
        sa.Column("feedback_value", sa.Float(), nullable=False, server_default="1"),
    )
    op.create_index("ix_feedback_events_user_id", "feedback_events", ["user_id"])
    op.create_index("ix_feedback_events_article_id", "feedback_events", ["article_id"])

    op.create_table(
        "recommendation_results",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("article_id", sa.String(32), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("ranking_score", sa.Float(), nullable=False),
        sa.Column("topic_match_score", sa.Float(), nullable=False),
        sa.Column("type_match_score", sa.Float(), nullable=False),
        sa.Column("style_match_score", sa.Float(), nullable=False),
        sa.Column("novelty_score", sa.Float(), nullable=False),
        sa.Column("freshness_score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text()),
    )
    op.create_index("ix_recommendation_results_user_id", "recommendation_results", ["user_id"])
    op.create_index("ix_recommendation_results_article_id", "recommendation_results", ["article_id"])

    op.create_table(
        "article_embeddings",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("article_id", sa.String(32), sa.ForeignKey("articles.id"), nullable=False, unique=True),
        sa.Column("embedding_model", sa.String(128), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
    )
    op.create_index("ix_article_embeddings_article_id", "article_embeddings", ["article_id"])
    op.create_index("ix_article_embeddings_content_hash", "article_embeddings", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_article_embeddings_content_hash", table_name="article_embeddings")
    op.drop_index("ix_article_embeddings_article_id", table_name="article_embeddings")
    op.drop_table("article_embeddings")

    op.drop_index("ix_recommendation_results_article_id", table_name="recommendation_results")
    op.drop_index("ix_recommendation_results_user_id", table_name="recommendation_results")
    op.drop_table("recommendation_results")

    op.drop_index("ix_feedback_events_article_id", table_name="feedback_events")
    op.drop_index("ix_feedback_events_user_id", table_name="feedback_events")
    op.drop_table("feedback_events")

    op.drop_index("ix_novelty_analyses_article_id", table_name="novelty_analyses")
    op.drop_table("novelty_analyses")

    op.drop_index("ix_article_metrics_article_id", table_name="article_metrics")
    op.drop_table("article_metrics")

    op.drop_index("ix_articles_title", table_name="articles")
    op.drop_index("ix_articles_publish_time", table_name="articles")
    op.drop_index("ix_articles_source_id", table_name="articles")
    op.drop_table("articles")

    op.drop_table("user_profiles")
    op.drop_table("article_sources")
