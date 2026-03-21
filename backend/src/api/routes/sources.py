from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.schemas.content import ArticleSourceCreate, ArticleSourceDeleteRead, ArticleSourceRead, ArticleSourceUpdate
from src.services.sources import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])
service = SourceService()


@router.get("", response_model=list[ArticleSourceRead])
def list_sources(db: Session = Depends(db_session)):
    return service.list_sources(db)


@router.post("", response_model=ArticleSourceRead)
def create_source(payload: ArticleSourceCreate, db: Session = Depends(db_session)):
    source = service.create_source(db, payload)
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


@router.delete("/{source_id}", response_model=ArticleSourceDeleteRead)
def delete_source(source_id: str, db: Session = Depends(db_session)):
    source = service.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source not found")
    result = service.delete_source(db, source)
    db.commit()
    return result
