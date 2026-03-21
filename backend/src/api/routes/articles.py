from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.schemas.content import (
    ArticleBatchDeletePayload,
    ArticleBatchDeleteRead,
    ArticleDeleteRead,
    ArticleListRead,
    ArticleRead,
)
from src.services.articles import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])
article_service = ArticleService()


@router.get("", response_model=ArticleListRead)
def list_articles(
    limit: int = 20,
    source_id: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int | None = None,
    sort: str = "latest",
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(db_session),
):
    safe_page_size = page_size or limit
    articles, total = article_service.list_articles(
        db,
        limit=limit,
        source_id=source_id,
        q=q,
        page=page,
        page_size=safe_page_size,
        sort=sort,
        date_from=date_from,
        date_to=date_to,
    )
    return ArticleListRead(
        items=article_service.to_summary_rows(articles),
        total=total,
        page=max(page, 1),
        page_size=max(safe_page_size, 1),
    )


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(article_id: str, db: Session = Depends(db_session)):
    article = article_service.get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article not found")
    return article


@router.delete("/{article_id}", response_model=ArticleDeleteRead)
def delete_article(article_id: str, db: Session = Depends(db_session)):
    article = article_service.get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article not found")
    payload = ArticleDeleteRead(article_id=article.id, title=article.title)
    article_service.delete_article(db, article)
    db.commit()
    return payload


@router.post("/batch-delete", response_model=ArticleBatchDeleteRead)
def batch_delete_articles(payload: ArticleBatchDeletePayload, db: Session = Depends(db_session)):
    deleted_ids = article_service.batch_delete_articles(db, payload.article_ids)
    db.commit()
    return ArticleBatchDeleteRead(deleted_count=len(deleted_ids), deleted_ids=deleted_ids)
