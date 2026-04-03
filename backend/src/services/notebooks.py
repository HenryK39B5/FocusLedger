from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload, selectinload

from src.core.config import Settings
from src.integrations.tts_worker import TTSWorkerClient
from src.llm.providers import build_provider
from src.models import Article, Notebook, NotebookArticle, NotebookChatMessage, NotebookPodcastScript
from src.schemas.content import (
    NotebookPodcastAudioCreate,
    NotebookPodcastAudioJobRead,
    NotebookChatMessageRead,
    NotebookChatRead,
    NotebookChatResponse,
    NotebookCreate,
    NotebookPodcastScriptDeleteRead,
    NotebookPodcastScriptGenerate,
    NotebookPodcastScriptListRead,
    NotebookPodcastScriptRead,
    NotebookPodcastSectionRead,
    NotebookRead,
    NotebookUpdate,
)
from src.services.articles import ArticleService


class NotebookService:
    def __init__(self) -> None:
        self.article_service = ArticleService()

    def _normalize_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("notebook name is required")
        return cleaned

    def _normalize_emoji(self, value: str | None) -> str:
        cleaned = (value or "").strip()
        return cleaned or "📒"

    def _normalize_description(self, value: str | None) -> str | None:
        cleaned = (value or "").strip()
        return cleaned or None

    def _base_query(self):
        return (
            select(Notebook)
            .options(
                selectinload(Notebook.notebook_articles)
                .joinedload(NotebookArticle.article)
                .joinedload(Article.source),
                selectinload(Notebook.chat_messages),
                selectinload(Notebook.podcast_scripts),
            )
            .order_by(Notebook.updated_at.desc(), Notebook.created_at.desc())
        )

    def _to_read(self, notebook: Notebook) -> NotebookRead:
        links = [link for link in (notebook.notebook_articles or []) if link.article is not None]
        articles = [link.article for link in links]
        return NotebookRead(
            id=notebook.id,
            name=notebook.name,
            emoji=notebook.emoji,
            description=notebook.description,
            article_count=len(articles),
            articles=self.article_service.to_summary_rows(articles),
            created_at=notebook.created_at,
            updated_at=notebook.updated_at,
        )

    def list_notebooks(self, db: Session) -> list[Notebook]:
        return list(db.scalars(self._base_query()).all())

    def get_notebook(self, db: Session, notebook_id: str) -> Notebook | None:
        stmt = self._base_query().where(Notebook.id == notebook_id)
        return db.scalar(stmt)

    def create_notebook(self, db: Session, payload: NotebookCreate) -> Notebook:
        notebook = Notebook(
            name=self._normalize_name(payload.name),
            emoji=self._normalize_emoji(payload.emoji),
            description=self._normalize_description(payload.description),
        )
        db.add(notebook)
        db.flush()
        return self.get_notebook(db, notebook.id) or notebook

    def update_notebook(self, db: Session, notebook: Notebook, payload: NotebookUpdate) -> Notebook:
        updates = payload.model_dump(exclude_unset=True)
        if "name" in updates and updates["name"] is not None:
            notebook.name = self._normalize_name(updates["name"])
        if "emoji" in updates:
            notebook.emoji = self._normalize_emoji(updates["emoji"])
        if "description" in updates:
            notebook.description = self._normalize_description(updates["description"])
        db.flush()
        return self.get_notebook(db, notebook.id) or notebook

    def delete_notebook(self, db: Session, notebook: Notebook) -> None:
        db.delete(notebook)
        db.flush()

    def add_articles(self, db: Session, notebook: Notebook, article_ids: list[str]) -> Notebook:
        cleaned_ids: list[str] = []
        seen: set[str] = set()
        for article_id in article_ids:
            value = article_id.strip()
            if value and value not in seen:
                cleaned_ids.append(value)
                seen.add(value)

        if not cleaned_ids:
            raise ValueError("at least one article is required")

        existing_ids = {link.article_id for link in (notebook.notebook_articles or [])}
        articles = list(
            db.scalars(
                select(Article)
                .options(joinedload(Article.source))
                .where(Article.id.in_(cleaned_ids))
            ).all()
        )
        for article in articles:
            if article.id in existing_ids:
                continue
            db.add(NotebookArticle(notebook_id=notebook.id, article_id=article.id))

        db.flush()
        return self.get_notebook(db, notebook.id) or notebook

    def remove_article(self, db: Session, notebook: Notebook, article_id: str) -> Notebook:
        target = next((link for link in (notebook.notebook_articles or []) if link.article_id == article_id), None)
        if target is None:
            raise ValueError("article not found in notebook")
        db.delete(target)
        db.flush()
        return self.get_notebook(db, notebook.id) or notebook

    def _message_to_read(self, message: NotebookChatMessage) -> NotebookChatMessageRead:
        return NotebookChatMessageRead(
            id=message.id,
            notebook_id=message.notebook_id,
            role=message.role,
            content=message.content,
            citations=list(message.citations or []),
            created_at=message.created_at,
            updated_at=message.updated_at,
        )

    def get_chat(self, db: Session, notebook: Notebook) -> NotebookChatRead:
        messages = list(notebook.chat_messages or [])
        return NotebookChatRead(
            notebook_id=notebook.id,
            messages=[self._message_to_read(message) for message in messages],
        )

    def clear_chat(self, db: Session, notebook: Notebook) -> None:
        db.execute(delete(NotebookChatMessage).where(NotebookChatMessage.notebook_id == notebook.id))
        db.flush()

    def _podcast_to_read(self, script: NotebookPodcastScript) -> NotebookPodcastScriptRead:
        sections_raw = script.script_json.get("sections") if isinstance(script.script_json, dict) else []
        sections: list[NotebookPodcastSectionRead] = []
        if isinstance(sections_raw, list):
            for section in sections_raw:
                if not isinstance(section, dict):
                    continue
                sections.append(NotebookPodcastSectionRead(**section))
        return NotebookPodcastScriptRead(
            id=script.id,
            notebook_id=script.notebook_id,
            title=script.title,
            format=script.format,
            target_minutes=script.target_minutes,
            focus_prompt=script.focus_prompt,
            status=script.status,
            audio_status=script.audio_status,
            audio_job_id=script.audio_job_id,
            audio_path=script.audio_path,
            audio_error=script.audio_error,
            generation_error=script.generation_error,
            cited_article_ids=list(script.cited_article_ids or []),
            script_markdown=script.script_markdown,
            script_json=script.script_json or {},
            sections=sections,
            created_at=script.created_at,
            updated_at=script.updated_at,
        )

    def _audio_to_read(self, script: NotebookPodcastScript) -> NotebookPodcastAudioJobRead:
        return NotebookPodcastAudioJobRead(
            notebook_id=script.notebook_id,
            script_id=script.id,
            title=script.title,
            audio_status=script.audio_status,
            audio_job_id=script.audio_job_id,
            audio_path=script.audio_path,
            audio_error=script.audio_error,
            created_at=script.created_at,
            updated_at=script.updated_at,
        )

    def list_podcast_scripts(self, notebook: Notebook) -> NotebookPodcastScriptListRead:
        return NotebookPodcastScriptListRead(
            items=[self._podcast_to_read(item) for item in (notebook.podcast_scripts or [])],
        )

    def get_podcast_script(self, db: Session, notebook_id: str, script_id: str) -> NotebookPodcastScript | None:
        return db.scalar(
            select(NotebookPodcastScript).where(
                NotebookPodcastScript.notebook_id == notebook_id,
                NotebookPodcastScript.id == script_id,
            )
        )

    def _render_podcast_markdown(self, payload: dict[str, object]) -> str:
        title = str(payload.get("title") or "Podcast Script").strip()
        one_line_summary = str(payload.get("one_line_summary") or "").strip()
        lines = [f"# {title}", ""]
        if one_line_summary:
            lines.extend([one_line_summary, ""])
        sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
        for section in sections:
            if not isinstance(section, dict):
                continue
            lines.append(f"## {str(section.get('title') or 'Untitled').strip()}")
            objective = str(section.get("objective") or "").strip()
            if objective:
                lines.append(f"> {objective}")
            turns = section.get("turns") if isinstance(section.get("turns"), list) else []
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                text = str(turn.get("text") or "").strip()
                if not text:
                    continue
                lines.append("")
                lines.append(text)
                citations = [str(item).strip() for item in (turn.get("citations") or []) if str(item).strip()]
                if citations:
                    lines.append("")
                    lines.append(f"参考来源：{', '.join(citations)}")
            lines.append("")
        return "\n".join(lines).strip()

    def _render_podcast_audio_text(self, script: NotebookPodcastScript) -> str:
        sections_raw = script.script_json.get("sections") if isinstance(script.script_json, dict) else []
        chunks: list[str] = []
        if isinstance(sections_raw, list):
            for section in sections_raw:
                if not isinstance(section, dict):
                    continue
                turns = section.get("turns") if isinstance(section.get("turns"), list) else []
                for turn in turns:
                    if not isinstance(turn, dict):
                        continue
                    text = str(turn.get("text") or "").strip()
                    if text:
                        chunks.append(text)
        rendered = "\n\n".join(chunks).strip()
        return rendered or script.script_markdown.strip()

    def generate_podcast_script(
        self,
        db: Session,
        settings: Settings,
        notebook: Notebook,
        payload: NotebookPodcastScriptGenerate,
    ) -> NotebookPodcastScript:
        provider = build_provider(settings)
        if provider.name == "rule":
            raise ValueError("LLM provider unavailable; please configure a real LLM API first")
        if not notebook.notebook_articles:
            raise ValueError("notebook has no source articles")

        allowed_formats = {"brief", "explainer", "commentary"}
        podcast_format = (payload.format or "explainer").strip().lower()
        if podcast_format not in allowed_formats:
            raise ValueError("invalid podcast format")

        target_minutes = max(2, min(int(payload.target_minutes or 5), 20))
        selected_ids = {item.strip() for item in payload.article_ids if item.strip()}
        links = list(notebook.notebook_articles or [])
        if selected_ids:
            links = [link for link in links if link.article_id in selected_ids]
        if not links:
            raise ValueError("no notebook source articles selected")

        article_payload: list[dict[str, str | list[str] | None]] = []
        for link in links[:10]:
            article = link.article
            if article is None:
                continue
            article_payload.append(
                {
                    "id": article.id,
                    "title": article.title,
                    "source_name": article.source.name if article.source else "",
                    "publish_time": article.publish_time or "",
                    "summary": (article.summary or "").strip() or None,
                    "content_type": article.content_type,
                    "tags": list(article.tags or []),
                    "content": (article.raw_text or article.summary or "").strip()[:2200],
                }
            )
        if not article_payload:
            raise ValueError("selected notebook articles are missing usable text")

        generated = provider.generate_podcast_script(
            notebook_name=notebook.name,
            notebook_description=notebook.description,
            podcast_format=podcast_format,
            target_minutes=target_minutes,
            focus_prompt=(payload.focus_prompt or "").strip() or None,
            articles=article_payload,
        )

        script_payload = {
            "title": generated.get("title"),
            "format": podcast_format,
            "target_minutes": target_minutes,
            "one_line_summary": generated.get("one_line_summary"),
            "speakers": generated.get("speakers") or [{"id": "host", "display_name": "主持人", "voice_hint": "single_host"}],
            "sections": generated.get("sections") or [],
            "cited_article_ids": generated.get("cited_article_ids") or [],
        }
        markdown = self._render_podcast_markdown(script_payload)
        script = NotebookPodcastScript(
            notebook_id=notebook.id,
            title=str(script_payload["title"] or f"{notebook.name} Podcast").strip(),
            format=podcast_format,
            target_minutes=target_minutes,
            focus_prompt=(payload.focus_prompt or "").strip() or None,
            status="completed",
            audio_status="not_ready",
            audio_job_id=None,
            audio_path=None,
            audio_error=None,
            generation_error=None,
            cited_article_ids=list(script_payload.get("cited_article_ids") or []),
            script_markdown=markdown,
            script_json=script_payload,
        )
        db.add(script)
        db.flush()
        return script

    def create_podcast_audio_job(
        self,
        db: Session,
        settings: Settings,
        script: NotebookPodcastScript,
        options: NotebookPodcastAudioCreate | None = None,
    ) -> NotebookPodcastScript:
        if script.status != "completed":
            raise ValueError("podcast script is not ready")

        text = self._render_podcast_audio_text(script)
        if not text:
            raise ValueError("podcast script is empty")

        voice = (options.voice if options else None) or "zh-CN-XiaoxiaoNeural"
        rate = (options.rate if options else None) or "-8%"

        client = TTSWorkerClient(settings)
        job = client.create_job(
            text=text,
            filename_prefix=f"podcast-{script.id[:8]}",
            format="mp3",
            voice=voice,
            rate=rate,
        )

        script.audio_status = str(job.get("status") or "queued")
        script.audio_job_id = str(job["job_id"])
        script.audio_path = None
        script.audio_error = None
        db.flush()
        return script

    def refresh_podcast_audio_job(
        self,
        db: Session,
        settings: Settings,
        script: NotebookPodcastScript,
    ) -> NotebookPodcastScript:
        if not script.audio_job_id:
            return script

        client = TTSWorkerClient(settings)
        job = client.get_job(script.audio_job_id)
        script.audio_status = str(job.get("status") or script.audio_status or "queued")
        script.audio_error = str(job.get("error") or "").strip() or None

        if script.audio_status == "succeeded":
            script.audio_path = client.resolve_output_path(job.get("output_path"))
        elif script.audio_status in {"queued", "running"}:
            script.audio_path = None

        db.flush()
        return script

    def delete_podcast_script(self, db: Session, script: NotebookPodcastScript) -> NotebookPodcastScriptDeleteRead:
        payload = NotebookPodcastScriptDeleteRead(
            notebook_id=script.notebook_id,
            script_id=script.id,
            title=script.title,
        )
        db.delete(script)
        db.flush()
        return payload

    def ask(
        self,
        db: Session,
        settings: Settings,
        notebook: Notebook,
        question: str,
        *,
        history_limit: int = 6,
        article_limit: int = 8,
        article_char_limit: int = 1600,
    ) -> NotebookChatResponse:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("message is required")

        if not notebook.notebook_articles:
            raise ValueError("notebook has no source articles")

        provider = build_provider(settings)
        if provider.name == "rule":
            raise ValueError("LLM provider unavailable; please configure a real LLM API first")

        history_messages = list(notebook.chat_messages or [])[-history_limit:]
        history_payload = [
            {"role": message.role, "content": message.content}
            for message in history_messages
        ]

        article_payload: list[dict[str, str]] = []
        for link in list(notebook.notebook_articles or [])[:article_limit]:
            article = link.article
            if article is None:
                continue
            article_text = (article.raw_text or article.summary or "").strip()
            article_payload.append(
                {
                    "id": article.id,
                    "title": article.title,
                    "source_name": article.source.name if article.source else "",
                    "publish_time": article.publish_time or "",
                    "summary": (article.summary or "").strip(),
                    "content": article_text[:article_char_limit],
                }
            )

        if not article_payload:
            raise ValueError("notebook source articles are missing usable text")

        answer_payload = provider.answer_notebook_question(
            notebook_name=notebook.name,
            notebook_description=notebook.description,
            history=history_payload,
            articles=article_payload,
            question=cleaned_question,
        )

        user_message = NotebookChatMessage(
            notebook_id=notebook.id,
            role="user",
            content=cleaned_question,
            citations=[],
        )
        assistant_message = NotebookChatMessage(
            notebook_id=notebook.id,
            role="assistant",
            content=str(answer_payload.get("answer") or "").strip(),
            citations=list(answer_payload.get("citations") or []),
        )
        db.add(user_message)
        db.add(assistant_message)
        db.flush()

        return NotebookChatResponse(
            notebook_id=notebook.id,
            user_message=self._message_to_read(user_message),
            assistant_message=self._message_to_read(assistant_message),
        )


notebook_service = NotebookService()
