from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys

from sqlalchemy import delete, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.session import SessionLocal
from src.integrations.wechat_ingestion.utils.discovery import normalize_wechat_article_url
from src.models import (
    Article,
    ArticleEmbedding,
    ArticleMetrics,
    FeedbackEvent,
    NoveltyAnalysis,
    RecommendationResult,
)


def choose_keeper(rows: list[Article]) -> Article:
    return min(rows, key=lambda article: (article.created_at, article.id))


def cleanup_duplicates() -> tuple[int, int]:
    merged_count = 0
    normalized_count = 0
    with SessionLocal() as db:
        articles = list(db.scalars(select(Article).order_by(Article.created_at.asc(), Article.id.asc())).all())
        groups: dict[str, list[Article]] = defaultdict(list)
        for article in articles:
            normalized_url = normalize_wechat_article_url(article.url)
            groups[normalized_url].append(article)

        for canonical_url, rows in groups.items():
            keeper = choose_keeper(rows)
            if keeper.url != canonical_url:
                keeper.url = canonical_url
                normalized_count += 1

            duplicates = [row for row in rows if row.id != keeper.id]
            if not duplicates:
                continue

            duplicate_ids = [row.id for row in duplicates]
            db.execute(delete(ArticleEmbedding).where(ArticleEmbedding.article_id.in_(duplicate_ids)))
            db.execute(delete(ArticleMetrics).where(ArticleMetrics.article_id.in_(duplicate_ids)))
            db.execute(delete(NoveltyAnalysis).where(NoveltyAnalysis.article_id.in_(duplicate_ids)))
            db.execute(delete(RecommendationResult).where(RecommendationResult.article_id.in_(duplicate_ids)))
            db.execute(delete(FeedbackEvent).where(FeedbackEvent.article_id.in_(duplicate_ids)))

            for row in duplicates:
                db.delete(row)
            merged_count += len(duplicates)

        db.commit()
    return merged_count, normalized_count


if __name__ == "__main__":
    merged_count, normalized_count = cleanup_duplicates()
    print(f"merged={merged_count}, normalized={normalized_count}")
