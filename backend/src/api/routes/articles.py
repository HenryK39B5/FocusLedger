from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.core.config import get_settings
from src.schemas.content import (
    ArticleBatchAnalyzeRead,
    ArticleBatchAnalyzeQueryPayload,
    ArticleBatchDeletePayload,
    ArticleBatchDeleteRead,
    ArticleDeleteRead,
    ArticleImportPayload,
    ArticleImportResultRead,
    ArticleListRead,
    ArticleRead,
    ArticleUpdate,
)
from src.services.article_imports import ArticleImportService
from src.services.articles import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])
article_service = ArticleService()


@router.post("/import-links", response_model=ArticleImportResultRead)
def import_article_links(payload: ArticleImportPayload, db: Session = Depends(db_session)):
    service = ArticleImportService(get_settings())
    try:
        result = service.import_urls(db, payload.urls)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Article import failed: {exc}") from exc
    db.commit()
    return result


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
    llm_status: str | None = None,
    favorited_only: bool = False,
    tags: str | None = None,
    db: Session = Depends(db_session),
):
    safe_page_size = page_size or limit
    parsed_tags = [item.strip() for item in (tags or "").split(",") if item.strip()]
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
        llm_status=llm_status,
        favorited_only=favorited_only,
        tags=parsed_tags,
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


@router.put("/{article_id}", response_model=ArticleRead)
def update_article(article_id: str, payload: ArticleUpdate, db: Session = Depends(db_session)):
    article = article_service.get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article not found")
    article = article_service.update_article(db, article, payload)
    db.commit()
    return article_service.get_article(db, article_id)


@router.post("/{article_id}/analyze", response_model=ArticleRead)
def analyze_article(article_id: str, db: Session = Depends(db_session)):
    article = article_service.get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article not found")
    try:
        article = article_service.analyze_article(db, get_settings(), article)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"LLM analyze failed: {exc}") from exc
    db.commit()
    return article_service.get_article(db, article_id)


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


@router.post("/batch-analyze", response_model=ArticleBatchAnalyzeRead)
def batch_analyze_articles(payload: ArticleBatchDeletePayload, db: Session = Depends(db_session)):
    analyzed_ids, failed_ids = article_service.batch_analyze_articles(db, get_settings(), payload.article_ids)
    db.commit()
    return ArticleBatchAnalyzeRead(
        analyzed_count=len(analyzed_ids),
        analyzed_ids=analyzed_ids,
        failed_ids=failed_ids,
    )


@router.post("/batch-analyze-query", response_model=ArticleBatchAnalyzeRead)
def batch_analyze_articles_by_query(payload: ArticleBatchAnalyzeQueryPayload, db: Session = Depends(db_session)):
    try:
        analyzed_ids, failed_ids = article_service.batch_analyze_articles_by_query(
            db,
            get_settings(),
            source_id=payload.source_id,
            q=payload.q,
            date_from=payload.date_from,
            date_to=payload.date_to,
            favorited_only=payload.favorited_only,
            tags=payload.tags,
            max_items=payload.max_items,
            target=payload.target,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"LLM analyze failed: {exc}") from exc
    db.commit()
    return ArticleBatchAnalyzeRead(
        analyzed_count=len(analyzed_ids),
        analyzed_ids=analyzed_ids,
        failed_ids=failed_ids,
    )
