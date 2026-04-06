from __future__ import annotations

from pydantic import Field

from src.schemas.common import SchemaBase


class AgentArticleSearchRead(SchemaBase):
    id: str
    title: str
    source_id: str
    source_name: str
    publish_time: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_favorited: bool = False
    llm_summary_status: str = "pending"


class AgentArticleSearchResult(SchemaBase):
    total: int
    items: list[AgentArticleSearchRead] = Field(default_factory=list)


class AgentArticleImportPayload(SchemaBase):
    urls: list[str] = Field(default_factory=list)


class AgentArticleImportItemRead(SchemaBase):
    input_url: str
    status: str
    message: str
    article_id: str | None = None
    article_title: str | None = None
    source_name: str | None = None
    source_created: bool = False


class AgentArticleImportResult(SchemaBase):
    total: int
    imported_count: int
    updated_count: int
    failed_count: int
    source_created_count: int
    items: list[AgentArticleImportItemRead] = Field(default_factory=list)


class AgentArticleTagPayload(SchemaBase):
    article_ids: list[str] = Field(default_factory=list)
    add_tags: list[str] = Field(default_factory=list)
    remove_tags: list[str] = Field(default_factory=list)
    favorited: bool | None = None


class AgentArticleTagResult(SchemaBase):
    updated_count: int
    article_ids: list[str] = Field(default_factory=list)


class AgentArticleSummarizePayload(SchemaBase):
    article_ids: list[str] = Field(default_factory=list)


class AgentArticleSummarizeResult(SchemaBase):
    analyzed_count: int
    analyzed_ids: list[str] = Field(default_factory=list)
    failed_ids: list[str] = Field(default_factory=list)


class AgentNotebookRead(SchemaBase):
    id: str
    name: str
    emoji: str
    description: str | None = None
    article_count: int = 0


class AgentNotebookListRead(SchemaBase):
    total: int
    items: list[AgentNotebookRead] = Field(default_factory=list)


class AgentNotebookCreatePayload(SchemaBase):
    name: str
    emoji: str = "📒"
    description: str | None = None


class AgentNotebookUpdatePayload(SchemaBase):
    notebook_ref: str
    name: str | None = None
    emoji: str | None = None
    description: str | None = None


class AgentNotebookAddArticlesPayload(SchemaBase):
    notebook_ref: str
    article_ids: list[str] = Field(default_factory=list)


class AgentNotebookArticleRead(SchemaBase):
    id: str
    title: str
    source_name: str
    publish_time: str | None = None


class AgentNotebookDetailRead(SchemaBase):
    id: str
    name: str
    emoji: str
    description: str | None = None
    article_count: int = 0
    articles: list[AgentNotebookArticleRead] = Field(default_factory=list)


class AgentNotebookAskPayload(SchemaBase):
    notebook_ref: str
    message: str


class AgentNotebookAskRead(SchemaBase):
    notebook_id: str
    notebook_name: str
    answer: str
    citations: list[str] = Field(default_factory=list)


class AgentNotebookPodcastScriptPayload(SchemaBase):
    notebook_ref: str
    format: str = "explainer"
    target_minutes: int = 5
    focus_prompt: str | None = None
    article_ids: list[str] = Field(default_factory=list)


class AgentNotebookPodcastScriptRead(SchemaBase):
    notebook_id: str
    notebook_name: str
    script_id: str
    title: str
    format: str
    target_minutes: int
    script_markdown: str


class AgentNotebookPodcastScriptListRead(SchemaBase):
    total: int
    items: list[AgentNotebookPodcastScriptRead] = Field(default_factory=list)


class AgentNotebookPodcastAudioPayload(SchemaBase):
    notebook_ref: str
    script_id: str | None = None
    engine: str = "edge"
    voice: str = "zh-CN-XiaoxiaoNeural"
    voice_mode: str | None = None
    rate: str = "-8%"


class AgentNotebookPodcastAudioRead(SchemaBase):
    notebook_id: str
    notebook_name: str
    script_id: str
    script_title: str
    audio_status: str
    audio_job_id: str | None = None
    audio_path: str | None = None
    audio_error: str | None = None
