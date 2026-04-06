from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.models import Article, ArticleSource, Notebook
from src.schemas.agent import (
    AgentArticleImportItemRead,
    AgentArticleImportResult,
    AgentArticleSearchRead,
    AgentArticleSearchResult,
    AgentNotebookArticleRead,
    AgentNotebookAskRead,
    AgentNotebookDetailRead,
    AgentNotebookListRead,
    AgentNotebookPodcastAudioRead,
    AgentNotebookPodcastScriptListRead,
    AgentNotebookPodcastScriptRead,
    AgentNotebookRead,
)
from src.schemas.content import NotebookCreate, NotebookPodcastAudioCreate, NotebookPodcastScriptGenerate, NotebookUpdate
from src.services.article_imports import ArticleImportService
from src.services.articles import ArticleService
from src.services.notebooks import notebook_service


class AgentService:
    def __init__(self) -> None:
        self.article_service = ArticleService()

    def search_articles(
        self,
        db: Session,
        *,
        q: str | None = None,
        source_name: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        favorited_only: bool = False,
        limit: int = 10,
    ) -> AgentArticleSearchResult:
        source_id = self._resolve_source_id_by_name(db, source_name) if source_name else None
        articles, total = self.article_service.list_articles(
            db,
            source_id=source_id,
            q=q,
            page=1,
            page_size=max(1, min(limit, 50)),
            sort="latest",
            date_from=date_from,
            date_to=date_to,
            favorited_only=favorited_only,
            tags=tags or [],
        )
        return AgentArticleSearchResult(
            total=total,
            items=[
                AgentArticleSearchRead(
                    id=article.id,
                    title=article.title,
                    source_id=article.source_id,
                    source_name=article.source.name if article.source else "",
                    publish_time=article.publish_time,
                    tags=list(article.tags or []),
                    is_favorited=article.is_favorited,
                    llm_summary_status=article.llm_summary_status,
                )
                for article in articles
            ],
        )

    def import_articles(self, db: Session, settings: Settings, urls: list[str]) -> AgentArticleImportResult:
        result = ArticleImportService(settings).import_urls(db, urls)
        return AgentArticleImportResult(
            total=result.total,
            imported_count=result.imported_count,
            updated_count=result.updated_count,
            failed_count=result.failed_count,
            source_created_count=result.source_created_count,
            items=[
                AgentArticleImportItemRead(
                    input_url=item.input_url,
                    status=item.status,
                    message=item.message,
                    article_id=item.article_id,
                    article_title=item.article_title,
                    source_name=item.source_name,
                    source_created=item.source_created,
                )
                for item in result.items
            ],
        )

    def update_article_tags(
        self,
        db: Session,
        *,
        article_ids: list[str],
        add_tags: list[str],
        remove_tags: list[str],
        favorited: bool | None = None,
    ) -> list[str]:
        cleaned_ids = self._clean_ids(article_ids)
        if not cleaned_ids:
            raise ValueError("at least one article_id is required")
        articles = list(db.scalars(select(Article).where(Article.id.in_(cleaned_ids))).all())
        found_ids: list[str] = []
        cleaned_add = self._clean_tags(add_tags)
        cleaned_remove = set(self._clean_tags(remove_tags))
        for article in articles:
            next_tags = [tag for tag in self._clean_tags(article.tags) if tag not in cleaned_remove]
            for tag in cleaned_add:
                if tag not in next_tags:
                    next_tags.append(tag)
            article.topic_tags = next_tags
            if favorited is not None:
                article.is_favorited = favorited
            db.flush()
            found_ids.append(article.id)
        return found_ids

    def summarize_articles(self, db: Session, settings: Settings, article_ids: list[str]) -> tuple[list[str], list[str]]:
        cleaned_ids = self._clean_ids(article_ids)
        if not cleaned_ids:
            raise ValueError("at least one article_id is required")
        return self.article_service.batch_analyze_articles(db, settings, cleaned_ids)

    def list_notebooks(self, db: Session, query: str | None = None, limit: int = 20) -> AgentNotebookListRead:
        notebooks = notebook_service.list_notebooks(db)
        if query:
            keyword = query.strip().lower()
            notebooks = [item for item in notebooks if keyword in item.name.lower()]
        notebooks = notebooks[: max(1, min(limit, 50))]
        return AgentNotebookListRead(
            total=len(notebooks),
            items=[
                AgentNotebookRead(
                    id=item.id,
                    name=item.name,
                    emoji=item.emoji,
                    description=item.description,
                    article_count=len(item.notebook_articles or []),
                )
                for item in notebooks
            ],
        )

    def get_notebook_detail(self, db: Session, notebook_ref: str) -> AgentNotebookDetailRead:
        notebook = self._resolve_notebook(db, notebook_ref)
        articles = [
            AgentNotebookArticleRead(
                id=link.article.id,
                title=link.article.title,
                source_name=link.article.source.name if link.article.source else "",
                publish_time=link.article.publish_time,
            )
            for link in (notebook.notebook_articles or [])
            if link.article is not None
        ]
        return AgentNotebookDetailRead(
            id=notebook.id,
            name=notebook.name,
            emoji=notebook.emoji,
            description=notebook.description,
            article_count=len(articles),
            articles=articles,
        )

    def create_notebook(self, db: Session, *, name: str, emoji: str, description: str | None) -> AgentNotebookRead:
        notebook = notebook_service.create_notebook(
            db,
            NotebookCreate(name=name, emoji=emoji, description=description),
        )
        return AgentNotebookRead(
            id=notebook.id,
            name=notebook.name,
            emoji=notebook.emoji,
            description=notebook.description,
            article_count=len(notebook.notebook_articles or []),
        )

    def update_notebook(
        self,
        db: Session,
        *,
        notebook_ref: str,
        name: str | None,
        emoji: str | None,
        description: str | None,
    ) -> AgentNotebookRead:
        notebook = self._resolve_notebook(db, notebook_ref)
        updates: dict[str, str | None] = {}
        if name is not None:
            updates["name"] = name
        if emoji is not None:
            updates["emoji"] = emoji
        if description is not None:
            updates["description"] = description
        notebook = notebook_service.update_notebook(db, notebook, NotebookUpdate(**updates))
        return AgentNotebookRead(
            id=notebook.id,
            name=notebook.name,
            emoji=notebook.emoji,
            description=notebook.description,
            article_count=len(notebook.notebook_articles or []),
        )

    def add_articles_to_notebook(
        self,
        db: Session,
        *,
        notebook_ref: str,
        article_ids: list[str],
    ) -> AgentNotebookDetailRead:
        notebook = self._resolve_notebook(db, notebook_ref)
        notebook = notebook_service.add_articles(db, notebook, self._clean_ids(article_ids))
        return self.get_notebook_detail(db, notebook.id)

    def ask_notebook(self, db: Session, settings: Settings, *, notebook_ref: str, message: str) -> AgentNotebookAskRead:
        notebook = self._resolve_notebook(db, notebook_ref)
        response = notebook_service.ask(db, settings, notebook, message)
        return AgentNotebookAskRead(
            notebook_id=notebook.id,
            notebook_name=notebook.name,
            answer=response.assistant_message.content,
            citations=response.assistant_message.citations,
        )

    def generate_notebook_podcast_script(
        self,
        db: Session,
        settings: Settings,
        *,
        notebook_ref: str,
        podcast_format: str,
        target_minutes: int,
        focus_prompt: str | None,
        article_ids: list[str],
    ) -> AgentNotebookPodcastScriptRead:
        notebook = self._resolve_notebook(db, notebook_ref)
        script = notebook_service.generate_podcast_script(
            db,
            settings,
            notebook,
            NotebookPodcastScriptGenerate(
                format=podcast_format,
                target_minutes=target_minutes,
                focus_prompt=focus_prompt,
                article_ids=self._clean_ids(article_ids),
            ),
        )
        return AgentNotebookPodcastScriptRead(
            notebook_id=notebook.id,
            notebook_name=notebook.name,
            script_id=script.id,
            title=script.title,
            format=script.format,
            target_minutes=script.target_minutes,
            script_markdown=script.script_markdown,
        )

    def list_notebook_podcast_scripts(self, db: Session, *, notebook_ref: str) -> AgentNotebookPodcastScriptListRead:
        notebook = self._resolve_notebook(db, notebook_ref)
        items = [
            AgentNotebookPodcastScriptRead(
                notebook_id=notebook.id,
                notebook_name=notebook.name,
                script_id=script.id,
                title=script.title,
                format=script.format,
                target_minutes=script.target_minutes,
                script_markdown=script.script_markdown,
            )
            for script in (notebook.podcast_scripts or [])
        ]
        return AgentNotebookPodcastScriptListRead(total=len(items), items=items)

    def get_notebook_podcast_script(
        self,
        db: Session,
        *,
        notebook_ref: str,
        script_id: str,
    ) -> AgentNotebookPodcastScriptRead:
        notebook = self._resolve_notebook(db, notebook_ref)
        script = self._resolve_script(db, notebook.id, script_id)
        return AgentNotebookPodcastScriptRead(
            notebook_id=notebook.id,
            notebook_name=notebook.name,
            script_id=script.id,
            title=script.title,
            format=script.format,
            target_minutes=script.target_minutes,
            script_markdown=script.script_markdown,
        )

    def generate_notebook_podcast_audio(
        self,
        db: Session,
        settings: Settings,
        *,
        notebook_ref: str,
        script_id: str | None,
        engine: str,
        voice: str,
        voice_mode: str | None,
        rate: str,
    ) -> AgentNotebookPodcastAudioRead:
        notebook = self._resolve_notebook(db, notebook_ref)
        script = self._resolve_script(db, notebook.id, script_id)
        script = notebook_service.create_podcast_audio_job(
            db,
            settings,
            script,
            NotebookPodcastAudioCreate(
                engine=engine,
                voice=voice,
                voice_mode=voice_mode,
                rate=rate,
            ),
        )
        return AgentNotebookPodcastAudioRead(
            notebook_id=notebook.id,
            notebook_name=notebook.name,
            script_id=script.id,
            script_title=script.title,
            audio_status=script.audio_status,
            audio_job_id=script.audio_job_id,
            audio_path=script.audio_path,
            audio_error=script.audio_error,
        )

    def get_notebook_podcast_audio_status(
        self,
        db: Session,
        settings: Settings,
        *,
        notebook_ref: str,
        script_id: str,
    ) -> AgentNotebookPodcastAudioRead:
        notebook = self._resolve_notebook(db, notebook_ref)
        script = self._resolve_script(db, notebook.id, script_id)
        script = notebook_service.refresh_podcast_audio_job(db, settings, script)
        return AgentNotebookPodcastAudioRead(
            notebook_id=notebook.id,
            notebook_name=notebook.name,
            script_id=script.id,
            script_title=script.title,
            audio_status=script.audio_status,
            audio_job_id=script.audio_job_id,
            audio_path=script.audio_path,
            audio_error=script.audio_error,
        )

    def _resolve_source_id_by_name(self, db: Session, source_name: str) -> str:
        cleaned = source_name.strip()
        if not cleaned:
            raise ValueError("source_name is required")
        exact = db.scalar(select(ArticleSource).where(func.lower(ArticleSource.name) == cleaned.lower()))
        if exact:
            return exact.id
        matched = list(
            db.scalars(select(ArticleSource).where(func.lower(ArticleSource.name).like(f"%{cleaned.lower()}%"))).all()
        )
        if not matched:
            raise ValueError("source not found")
        if len(matched) > 1:
            raise ValueError("multiple sources matched; please use a more specific source name")
        return matched[0].id

    def _resolve_notebook(self, db: Session, notebook_ref: str) -> Notebook:
        cleaned = notebook_ref.strip()
        notebook = notebook_service.get_notebook(db, cleaned)
        if notebook:
            return notebook
        exact = db.scalar(select(Notebook).where(func.lower(Notebook.name) == cleaned.lower()))
        if exact:
            return notebook_service.get_notebook(db, exact.id) or exact
        matched = list(db.scalars(select(Notebook).where(func.lower(Notebook.name).like(f"%{cleaned.lower()}%"))).all())
        if not matched:
            raise ValueError("notebook not found")
        if len(matched) > 1:
            raise ValueError("multiple notebooks matched; please use a more specific notebook name")
        return notebook_service.get_notebook(db, matched[0].id) or matched[0]

    def _resolve_script(self, db: Session, notebook_id: str, script_id: str | None):
        if script_id:
            script = notebook_service.get_podcast_script(db, notebook_id, script_id)
            if not script:
                raise ValueError("podcast script not found")
            return script
        notebook = notebook_service.get_notebook(db, notebook_id)
        scripts = list(notebook.podcast_scripts or []) if notebook else []
        if not scripts:
            raise ValueError("no podcast script available for this notebook")
        return scripts[0]

    def _clean_ids(self, values: list[str]) -> list[str]:
        items: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if value and value not in items:
                items.append(value)
        return items

    def _clean_tags(self, values: list[str]) -> list[str]:
        tags: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if value and value not in tags:
                tags.append(value)
        return tags


agent_service = AgentService()
