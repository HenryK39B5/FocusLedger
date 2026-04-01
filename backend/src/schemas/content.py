from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from src.schemas.common import IDSchema, SchemaBase, TimestampSchema


class ArticleSourceCreate(SchemaBase):
    name: str
    source_type: str = "wechat_public_account"
    biz: str
    public_home_link: str | None = None
    credential_link: str
    source_group: str | None = None
    tags: list[str] = Field(default_factory=list)
    description: str | None = None
    enabled: bool = True


class ArticleSourceUpdate(SchemaBase):
    name: str | None = None
    source_group: str | None = None
    tags: list[str] | None = None
    description: str | None = None
    enabled: bool | None = None


class ArticleSourceDeleteRead(SchemaBase):
    source_id: str
    source_name: str
    deleted_article_count: int


class ArticleSourceRead(IDSchema, TimestampSchema):
    name: str
    source_type: str
    biz: str
    public_home_link: str
    source_group: str | None = None
    tags: list[str] = Field(default_factory=list)
    description: str | None = None
    enabled: bool
    credential_status: str
    last_verified_at: datetime | None = None
    last_sync_succeeded_at: datetime | None = None
    last_sync_failed_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    credential: "SourceCredentialRead | None" = None


class SourceCredentialRead(IDSchema, TimestampSchema):
    source_id: str
    provider: str
    raw_link: str
    token_biz: str
    uin: str
    appmsg_token: str | None = None
    session_us: str | None = None
    scene: str | None = None
    username: str | None = None


class SourceCredentialUpdate(SchemaBase):
    raw_link: str
    validate_after_update: bool = True


class SourceCredentialCheckRead(SchemaBase):
    source_id: str
    source_name: str
    valid: bool
    credential_status: str
    needs_refresh: bool = False
    error_code: str | None = None
    error_message: str | None = None
    last_verified_at: datetime | None = None
    message: str

class ArticleMetricRead(SchemaBase):
    read_count: int | None = None
    like_count: int | None = None
    repost_count: int | None = None
    comment_count: int | None = None
    comment_like_count: int | None = None
    captured_at: datetime


class ArticleRead(IDSchema, TimestampSchema):
    source_id: str
    title: str
    author: str | None = None
    publish_time: str | None = None
    url: str
    raw_html_path: str | None = None
    raw_text: str | None = None
    summary: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    entity_tags: list[str] = Field(default_factory=list)
    content_type: str | None = None
    core_claims: list[str] = Field(default_factory=list)
    key_variables: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    source: ArticleSourceRead | None = None
    metrics: list[ArticleMetricRead] = Field(default_factory=list)


class ArticleSummaryRead(SchemaBase):
    id: str
    title: str
    source_id: str
    source_name: str
    publish_time: str | None = None
    created_at: datetime
    summary: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    source_tags: list[str] = Field(default_factory=list)
    source_group: str | None = None


class ArticleListRead(SchemaBase):
    items: list[ArticleSummaryRead] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class ArticleDeleteRead(SchemaBase):
    article_id: str
    title: str


class ArticleBatchDeletePayload(SchemaBase):
    article_ids: list[str] = Field(default_factory=list)


class ArticleBatchDeleteRead(SchemaBase):
    deleted_count: int
    deleted_ids: list[str] = Field(default_factory=list)

ArticleSourceRead.model_rebuild()
ArticleRead.model_rebuild()
