from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.core.config import get_settings
from src.schemas.agent import (
    AgentArticleImportPayload,
    AgentArticleImportResult,
    AgentArticleSearchResult,
    AgentArticleSummarizePayload,
    AgentArticleSummarizeResult,
    AgentArticleTagPayload,
    AgentArticleTagResult,
    AgentNotebookAddArticlesPayload,
    AgentNotebookAskPayload,
    AgentNotebookAskRead,
    AgentNotebookCreatePayload,
    AgentNotebookDetailRead,
    AgentNotebookListRead,
    AgentNotebookPodcastAudioPayload,
    AgentNotebookPodcastAudioRead,
    AgentNotebookPodcastScriptListRead,
    AgentNotebookPodcastScriptPayload,
    AgentNotebookPodcastScriptRead,
    AgentNotebookRead,
    AgentNotebookUpdatePayload,
)
from src.services.agent import agent_service

router = APIRouter(prefix="/integrations/agent", tags=["agent"])


def _authorize(x_integration_key: str | None) -> None:
    settings = get_settings()
    if settings.agent_integration_key and x_integration_key != settings.agent_integration_key:
        raise HTTPException(status_code=401, detail="invalid integration key")


@router.get("/articles/search", response_model=AgentArticleSearchResult)
def search_articles(
    q: str | None = None,
    source_name: str | None = None,
    tags: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    favorited_only: bool = False,
    limit: int = 10,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    parsed_tags = [item.strip() for item in (tags or "").split(",") if item.strip()]
    try:
        return agent_service.search_articles(
            db,
            q=q,
            source_name=source_name,
            tags=parsed_tags,
            date_from=date_from,
            date_to=date_to,
            favorited_only=favorited_only,
            limit=max(1, min(limit, 50)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/articles/import-links", response_model=AgentArticleImportResult)
def import_links(
    payload: AgentArticleImportPayload,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        result = agent_service.import_articles(db, get_settings(), payload.urls)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Agent article import failed: {exc}") from exc
    db.commit()
    return result


@router.post("/articles/tags", response_model=AgentArticleTagResult)
def update_article_tags(
    payload: AgentArticleTagPayload,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        updated_ids = agent_service.update_article_tags(
            db,
            article_ids=payload.article_ids,
            add_tags=payload.add_tags,
            remove_tags=payload.remove_tags,
            favorited=payload.favorited,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return AgentArticleTagResult(updated_count=len(updated_ids), article_ids=updated_ids)


@router.post("/articles/summarize", response_model=AgentArticleSummarizeResult)
def summarize_articles(
    payload: AgentArticleSummarizePayload,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        analyzed_ids, failed_ids = agent_service.summarize_articles(db, get_settings(), payload.article_ids)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Agent summarize failed: {exc}") from exc
    db.commit()
    return AgentArticleSummarizeResult(
        analyzed_count=len(analyzed_ids),
        analyzed_ids=analyzed_ids,
        failed_ids=failed_ids,
    )


@router.get("/notebooks", response_model=AgentNotebookListRead)
def list_notebooks(
    q: str | None = None,
    limit: int = 20,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    return agent_service.list_notebooks(db, query=q, limit=limit)


@router.get("/notebooks/{notebook_ref}", response_model=AgentNotebookDetailRead)
def get_notebook_detail(
    notebook_ref: str,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        return agent_service.get_notebook_detail(db, notebook_ref)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/notebooks", response_model=AgentNotebookRead)
def create_notebook(
    payload: AgentNotebookCreatePayload,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        result = agent_service.create_notebook(db, name=payload.name, emoji=payload.emoji, description=payload.description)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.post("/notebooks/update", response_model=AgentNotebookRead)
def update_notebook(
    payload: AgentNotebookUpdatePayload,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        result = agent_service.update_notebook(
            db,
            notebook_ref=payload.notebook_ref,
            name=payload.name,
            emoji=payload.emoji,
            description=payload.description,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.post("/notebooks/add-articles", response_model=AgentNotebookDetailRead)
def add_articles_to_notebook(
    payload: AgentNotebookAddArticlesPayload,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        result = agent_service.add_articles_to_notebook(
            db,
            notebook_ref=payload.notebook_ref,
            article_ids=payload.article_ids,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.post("/notebooks/ask", response_model=AgentNotebookAskRead)
def ask_notebook(
    payload: AgentNotebookAskPayload,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        result = agent_service.ask_notebook(db, get_settings(), notebook_ref=payload.notebook_ref, message=payload.message)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Agent notebook ask failed: {exc}") from exc
    db.commit()
    return result


@router.post("/notebooks/generate-podcast-script", response_model=AgentNotebookPodcastScriptRead)
def generate_podcast_script(
    payload: AgentNotebookPodcastScriptPayload,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        result = agent_service.generate_notebook_podcast_script(
            db,
            get_settings(),
            notebook_ref=payload.notebook_ref,
            podcast_format=payload.format,
            target_minutes=payload.target_minutes,
            focus_prompt=payload.focus_prompt,
            article_ids=payload.article_ids,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Agent podcast script generation failed: {exc}") from exc
    db.commit()
    return result


@router.get("/notebooks/{notebook_ref}/podcasts", response_model=AgentNotebookPodcastScriptListRead)
def list_podcast_scripts(
    notebook_ref: str,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        return agent_service.list_notebook_podcast_scripts(db, notebook_ref=notebook_ref)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/notebooks/{notebook_ref}/podcasts/{script_id}", response_model=AgentNotebookPodcastScriptRead)
def get_podcast_script(
    notebook_ref: str,
    script_id: str,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        return agent_service.get_notebook_podcast_script(db, notebook_ref=notebook_ref, script_id=script_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/notebooks/generate-podcast-audio", response_model=AgentNotebookPodcastAudioRead)
def generate_podcast_audio(
    payload: AgentNotebookPodcastAudioPayload,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        result = agent_service.generate_notebook_podcast_audio(
            db,
            get_settings(),
            notebook_ref=payload.notebook_ref,
            script_id=payload.script_id,
            engine=payload.engine,
            voice=payload.voice,
            voice_mode=payload.voice_mode,
            rate=payload.rate,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Agent podcast audio generation failed: {exc}") from exc
    db.commit()
    return result


@router.get("/notebooks/{notebook_ref}/podcasts/{script_id}/audio", response_model=AgentNotebookPodcastAudioRead)
def get_podcast_audio_status(
    notebook_ref: str,
    script_id: str,
    x_integration_key: str | None = Header(default=None),
    db: Session = Depends(db_session),
):
    _authorize(x_integration_key)
    try:
        result = agent_service.get_notebook_podcast_audio_status(
            db,
            get_settings(),
            notebook_ref=notebook_ref,
            script_id=script_id,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Agent podcast audio status failed: {exc}") from exc
    db.commit()
    return result
