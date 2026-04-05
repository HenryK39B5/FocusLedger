from __future__ import annotations

import json
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.integrations.wechat_ingestion.core.base_spider import BaseSpider
from src.integrations.wechat_ingestion.utils.discovery import normalize_wechat_article_url
from src.integrations.wechat_ingestion.utils.tools import article_storage_dir, ensure_dir
from src.llm.providers import build_provider
from src.models import Article, ArticleEmbedding, ArticleSource
from src.schemas.content import ArticleImportItemRead, ArticleImportResultRead, ArticleSourceCreate
from src.services.sources import SourceService


class ArticleImportService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.spider = BaseSpider(timeout=settings.request_timeout_seconds, verify_ssl=settings.wechat_verify_ssl)
        self.provider = build_provider(settings)
        self.source_service = SourceService()

    def import_urls(self, db: Session, urls: list[str]) -> ArticleImportResultRead:
        normalized_inputs: list[str] = []
        seen: set[str] = set()
        for raw in urls:
            cleaned = str(raw or "").strip()
            if not cleaned:
                continue
            canonical = normalize_wechat_article_url(cleaned)
            if canonical in seen:
                continue
            seen.add(canonical)
            normalized_inputs.append(cleaned)

        items: list[ArticleImportItemRead] = []
        imported_count = 0
        updated_count = 0
        failed_count = 0
        source_created_count = 0

        for raw_url in normalized_inputs:
            item = self.import_url(db, raw_url)
            items.append(item)
            if item.status == "imported":
                imported_count += 1
            elif item.status == "updated":
                updated_count += 1
            else:
                failed_count += 1
            if item.source_created:
                source_created_count += 1

        return ArticleImportResultRead(
            total=len(normalized_inputs),
            imported_count=imported_count,
            updated_count=updated_count,
            failed_count=failed_count,
            source_created_count=source_created_count,
            items=items,
        )

    def import_url(self, db: Session, raw_url: str) -> ArticleImportItemRead:
        canonical_input = normalize_wechat_article_url(raw_url)
        fetch_result = self.spider.fetch_article_html(raw_url)
        if not fetch_result.ok or not fetch_result.html:
            return ArticleImportItemRead(
                input_url=raw_url,
                normalized_url=canonical_input,
                status="failed",
                message=fetch_result.error or "获取文章失败。",
            )

        parsed = self.spider.parse_article_html(fetch_result.html, raw_url)
        biz = str(parsed.metadata.get("biz") or "").strip()
        if not biz:
            return ArticleImportItemRead(
                input_url=raw_url,
                normalized_url=canonical_input,
                status="failed",
                message="无法从文章页面解析公众号 __biz。",
            )

        source, source_created = self._ensure_source(
            db,
            biz=biz,
            source_name=parsed.source_name,
            public_home_link=str(parsed.metadata.get("public_home_link") or "").strip() or None,
        )

        article_status, article = self._upsert_article(
            db,
            source=source,
            fetch_url=raw_url,
            canonical_input=canonical_input,
            html_url=fetch_result.url or raw_url,
            parsed=parsed,
        )

        return ArticleImportItemRead(
            input_url=raw_url,
            normalized_url=article.url,
            status=article_status,
            message="文章已加入文章库。" if article_status == "imported" else "文章已更新到文章库。",
            article_id=article.id,
            article_title=article.title,
            source_id=source.id,
            source_name=source.name,
            source_created=source_created,
        )

    def _ensure_source(
        self,
        db: Session,
        *,
        biz: str,
        source_name: str | None,
        public_home_link: str | None,
    ) -> tuple[ArticleSource, bool]:
        existing = self.source_service.get_source_by_biz(db, biz)
        if existing:
            if public_home_link and not existing.public_home_link:
                existing.public_home_link = public_home_link
                db.flush()
            return existing, False

        payload = ArticleSourceCreate(
            name=(source_name or biz).strip(),
            biz=biz,
            public_home_link=public_home_link,
            credential_link=None,
            source_group=None,
            tags=[],
            description=None,
            enabled=True,
        )
        created = self.source_service.create_source(db, self.settings, payload)
        db.flush()
        return created, True

    def _upsert_article(
        self,
        db: Session,
        *,
        source: ArticleSource,
        fetch_url: str,
        canonical_input: str,
        html_url: str,
        parsed,
    ) -> tuple[str, Article]:
        parsed_url = normalize_wechat_article_url(parsed.url or canonical_input)
        storage_path = article_storage_dir(
            self.settings.article_storage_path,
            source.name,
            parsed.publish_time,
            parsed.title,
        )
        saved_html = self._write_article_snapshot(storage_path, fetch_url=fetch_url, html_url=html_url, html=parsed.html)

        existing = db.scalar(select(Article).where(Article.url == parsed_url))
        article = existing or Article(source_id=source.id, url=parsed_url)
        article.source_id = source.id
        article.title = parsed.title
        article.author = parsed.author
        article.publish_time = parsed.publish_time
        article.raw_html_path = saved_html
        article.raw_text = parsed.text
        article.summary = article.summary if existing else None
        article.topic_tags = article.topic_tags if existing else []
        article.entity_tags = article.entity_tags if existing else []
        article.content_type = article.content_type if existing else None
        article.core_claims = article.core_claims if existing else []
        article.key_variables = article.key_variables if existing else []
        article.catalysts = article.catalysts if existing else []
        article.risks = article.risks if existing else []
        article.style_tags = article.style_tags if existing else []
        article.recommendation_reason = None
        article.is_favorited = article.is_favorited if existing else False
        article.llm_summary_status = "pending"
        article.llm_summary_error = None
        article.llm_summary_updated_at = None

        metadata = dict(parsed.metadata)
        metadata["canonical_article_url"] = parsed_url
        metadata["fetch_url"] = fetch_url
        article.metadata_json = metadata

        if not existing:
            db.add(article)
            db.flush()

        embedding_source = article.raw_text or parsed.text
        embedding = self.provider.embed_text(embedding_source)
        content_hash = sha256(embedding_source.encode("utf-8")).hexdigest()
        embedding_row = db.scalar(select(ArticleEmbedding).where(ArticleEmbedding.article_id == article.id))
        if embedding_row:
            embedding_row.embedding = embedding
            embedding_row.embedding_model = self.provider.name
            embedding_row.content_hash = content_hash
        else:
            db.add(
                ArticleEmbedding(
                    article_id=article.id,
                    embedding=embedding,
                    embedding_model=self.provider.name,
                    content_hash=content_hash,
                )
            )
        db.flush()
        return ("updated" if existing else "imported"), article

    def _write_article_snapshot(self, storage_path, *, fetch_url: str, html_url: str, html: str) -> str:
        target_dir = ensure_dir(storage_path)
        html_path = target_dir / "index.html"
        meta_path = target_dir / "page_meta.json"
        html_path.write_text(html, encoding="utf-8")
        meta_path.write_text(
            json.dumps({"fetch_url": fetch_url, "html_url": html_url}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(html_path)
