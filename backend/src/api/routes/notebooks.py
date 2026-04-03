from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.core.config import get_settings
from src.schemas.content import (
    NotebookChatRead,
    NotebookChatRequest,
    NotebookChatResponse,
    NotebookArticlePayload,
    NotebookPodcastAudioCreate,
    NotebookPodcastAudioJobRead,
    NotebookCreate,
    NotebookDeleteRead,
    NotebookListRead,
    NotebookPodcastScriptDeleteRead,
    NotebookPodcastScriptGenerate,
    NotebookPodcastScriptListRead,
    NotebookPodcastScriptRead,
    NotebookRead,
    NotebookUpdate,
)
from src.services.notebooks import notebook_service

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@router.get("", response_model=NotebookListRead)
def list_notebooks(db: Session = Depends(db_session)):
    notebooks = notebook_service.list_notebooks(db)
    return NotebookListRead(items=[notebook_service._to_read(item) for item in notebooks])


@router.post("", response_model=NotebookRead)
def create_notebook(payload: NotebookCreate, db: Session = Depends(db_session)):
    try:
        notebook = notebook_service.create_notebook(db, payload)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return notebook_service._to_read(notebook_service.get_notebook(db, notebook.id) or notebook)


@router.get("/{notebook_id}", response_model=NotebookRead)
def get_notebook(notebook_id: str, db: Session = Depends(db_session)):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    return notebook_service._to_read(notebook)


@router.put("/{notebook_id}", response_model=NotebookRead)
def update_notebook(notebook_id: str, payload: NotebookUpdate, db: Session = Depends(db_session)):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    try:
        notebook = notebook_service.update_notebook(db, notebook, payload)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return notebook_service._to_read(notebook_service.get_notebook(db, notebook_id) or notebook)


@router.delete("/{notebook_id}", response_model=NotebookDeleteRead)
def delete_notebook(notebook_id: str, db: Session = Depends(db_session)):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    payload = NotebookDeleteRead(notebook_id=notebook.id, name=notebook.name)
    notebook_service.delete_notebook(db, notebook)
    db.commit()
    return payload


@router.post("/{notebook_id}/articles", response_model=NotebookRead)
def add_notebook_articles(notebook_id: str, payload: NotebookArticlePayload, db: Session = Depends(db_session)):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    try:
        notebook = notebook_service.add_articles(db, notebook, payload.article_ids)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return notebook_service._to_read(notebook_service.get_notebook(db, notebook_id) or notebook)


@router.delete("/{notebook_id}/articles/{article_id}", response_model=NotebookRead)
def remove_notebook_article(notebook_id: str, article_id: str, db: Session = Depends(db_session)):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    try:
        notebook = notebook_service.remove_article(db, notebook, article_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return notebook_service._to_read(notebook_service.get_notebook(db, notebook_id) or notebook)


@router.get("/{notebook_id}/chat", response_model=NotebookChatRead)
def get_notebook_chat(notebook_id: str, db: Session = Depends(db_session)):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    return notebook_service.get_chat(db, notebook)


@router.post("/{notebook_id}/chat", response_model=NotebookChatResponse)
def ask_notebook_chat(notebook_id: str, payload: NotebookChatRequest, db: Session = Depends(db_session)):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    try:
        result = notebook_service.ask(db, get_settings(), notebook, payload.message)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Notebook chat failed: {exc}") from exc
    db.commit()
    return result


@router.delete("/{notebook_id}/chat", response_model=NotebookChatRead)
def clear_notebook_chat(notebook_id: str, db: Session = Depends(db_session)):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    notebook_service.clear_chat(db, notebook)
    db.commit()
    return NotebookChatRead(notebook_id=notebook.id, messages=[])


@router.get("/{notebook_id}/podcasts", response_model=NotebookPodcastScriptListRead)
def list_notebook_podcast_scripts(notebook_id: str, db: Session = Depends(db_session)):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    return notebook_service.list_podcast_scripts(notebook)


@router.post("/{notebook_id}/podcasts", response_model=NotebookPodcastScriptRead)
def generate_notebook_podcast_script(
    notebook_id: str,
    payload: NotebookPodcastScriptGenerate,
    db: Session = Depends(db_session),
):
    notebook = notebook_service.get_notebook(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="notebook not found")
    try:
        script = notebook_service.generate_podcast_script(db, get_settings(), notebook, payload)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Podcast script generation failed: {exc}") from exc
    db.commit()
    return notebook_service._podcast_to_read(script)


@router.get("/{notebook_id}/podcasts/{script_id}", response_model=NotebookPodcastScriptRead)
def get_notebook_podcast_script(notebook_id: str, script_id: str, db: Session = Depends(db_session)):
    script = notebook_service.get_podcast_script(db, notebook_id, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="podcast script not found")
    return notebook_service._podcast_to_read(script)


@router.post("/{notebook_id}/podcasts/{script_id}/audio", response_model=NotebookPodcastAudioJobRead)
def create_notebook_podcast_audio_job(
    notebook_id: str,
    script_id: str,
    payload: NotebookPodcastAudioCreate = NotebookPodcastAudioCreate(),
    db: Session = Depends(db_session),
):
    script = notebook_service.get_podcast_script(db, notebook_id, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="podcast script not found")
    try:
        script = notebook_service.create_podcast_audio_job(db, get_settings(), script, payload)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Podcast audio job creation failed: {exc}") from exc
    db.commit()
    return notebook_service._audio_to_read(script)


@router.get("/{notebook_id}/podcasts/{script_id}/audio", response_model=NotebookPodcastAudioJobRead)
def get_notebook_podcast_audio_job(notebook_id: str, script_id: str, db: Session = Depends(db_session)):
    script = notebook_service.get_podcast_script(db, notebook_id, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="podcast script not found")
    try:
        script = notebook_service.refresh_podcast_audio_job(db, get_settings(), script)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Podcast audio job refresh failed: {exc}") from exc
    db.commit()
    return notebook_service._audio_to_read(script)


@router.delete("/{notebook_id}/podcasts/{script_id}", response_model=NotebookPodcastScriptDeleteRead)
def delete_notebook_podcast_script(notebook_id: str, script_id: str, db: Session = Depends(db_session)):
    script = notebook_service.get_podcast_script(db, notebook_id, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="podcast script not found")
    payload = notebook_service.delete_podcast_script(db, script)
    db.commit()
    return payload
