from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.core.config import get_settings
from src.schemas.content import (
    ArticleSourceCreate,
    ArticleSourceDeleteRead,
    ArticleSourceRead,
    ArticleSourceUpdate,
    SourceBatchAnalyzeRead,
    SourceBatchPayload,
    SourceCredentialCheckRead,
    SourceCredentialUpdate,
)
from src.services.sources import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])
service = SourceService()


@router.get("", response_model=list[ArticleSourceRead])
def list_sources(db: Session = Depends(db_session)):
    return service.list_sources(db)


@router.post("", response_model=ArticleSourceRead)
def create_source(payload: ArticleSourceCreate, db: Session = Depends(db_session)):
    try:
        source = service.create_source(db, get_settings(), payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(source)
    return source


@router.put("/{source_id}", response_model=ArticleSourceRead)
def update_source(source_id: str, payload: ArticleSourceUpdate, db: Session = Depends(db_session)):
    source = service.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    source = service.update_source(db, source, payload)
    db.commit()
    db.refresh(source)
    return source


@router.post("/{source_id}/analyze", response_model=ArticleSourceRead)
def analyze_source(source_id: str, db: Session = Depends(db_session)):
    source = service.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    try:
        source = service.analyze_source(db, get_settings(), source)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"LLM source analyze failed: {exc}") from exc
    db.commit()
    db.refresh(source)
    return source


@router.post("/batch-analyze", response_model=SourceBatchAnalyzeRead)
def batch_analyze_sources(payload: SourceBatchPayload, db: Session = Depends(db_session)):
    try:
        result = service.batch_analyze_sources(db, get_settings(), payload.source_ids)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"LLM source analyze failed: {exc}") from exc
    db.commit()
    return result


@router.put("/{source_id}/credential", response_model=ArticleSourceRead)
def update_source_credential(source_id: str, payload: SourceCredentialUpdate, db: Session = Depends(db_session)):
    source = service.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    try:
        source, _ = service.update_source_credential(db, get_settings(), source, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(source)
    return source


@router.post("/{source_id}/credential/verify", response_model=SourceCredentialCheckRead)
def verify_source_credential(source_id: str, db: Session = Depends(db_session)):
    source = service.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    result = service.verify_source_credential(db, get_settings(), source)
    db.commit()
    return result


@router.delete("/{source_id}", response_model=ArticleSourceDeleteRead)
def delete_source(source_id: str, db: Session = Depends(db_session)):
    source = service.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    result = service.delete_source(db, source)
    db.commit()
    return result
