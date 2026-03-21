from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.integrations.wechat_ingestion.core.base_spider import BaseSpider
from src.integrations.wechat_ingestion.core.wechat_funcs import WeChatFuncs
from src.integrations.wechat_ingestion.storage.save_to_html import SaveWebpageToHtml
from src.integrations.wechat_ingestion.utils.discovery import normalize_wechat_article_url
from src.integrations.wechat_ingestion.utils.tools import article_storage_dir
from src.llm.providers import build_provider
from src.llm.taxonomy import TAXONOMY_VERSION
from src.models import Article, ArticleEmbedding, ArticleSource


@dataclass
class IngestionOutcome:
    imported_count: int = 0
    updated_count: int = 0
    failed_count: int = 0
    article_ids: list[str] | None = None
    message: str = ""

    def __post_init__(self) -> None:
        if self.article_ids is None:
            self.article_ids = []


class WechatIngestionPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.spider = BaseSpider(timeout=settings.request_timeout_seconds)
        self.wechat = WeChatFuncs(timeout=settings.request_timeout_seconds)
        self.storage = SaveWebpageToHtml()
        self.provider = build_provider(settings)

    def run(
        self,
        db: Session,
        source: ArticleSource,
        page_start: int = 1,
        page_end: int = 20,
        since_days: int | None = 7,
    ) -> IngestionOutcome:
        outcome = IngestionOutcome(message="采集完成")
        source_identifier = source.source_identifier or ""

        if "mp.weixin.qq.com" in source_identifier and "profile_ext" in source_identifier:
            token = self.wechat.parse_token_link(source_identifier)
            if not token:
                outcome.failed_count = 1
                outcome.message = (
                    "当前链接不是可用的公众号历史消息 token。请从 Fiddler 复制带有 "
                    "__biz、uin、key、pass_ticket 参数的 profile_ext 请求，优先使用 action=report。"
                )
                return outcome

            items = self.wechat.fetch_article_list(
                source_identifier,
                page_start,
                page_end,
                since_days=since_days,
            )
            seen_urls: set[str] = set()
            for item in items:
                canonical_url = normalize_wechat_article_url(item.url)
                if canonical_url in seen_urls:
                    continue
                seen_urls.add(canonical_url)
                self._ingest_article(
                    db=db,
                    source=source,
                    fetch_url=item.raw_url or item.url,
                    canonical_url=canonical_url,
                    title_hint=item.title,
                    outcome=outcome,
                )
            return outcome

        if source_identifier.startswith("http"):
            self._ingest_article(
                db=db,
                source=source,
                fetch_url=source_identifier,
                canonical_url=normalize_wechat_article_url(source_identifier),
                title_hint=source.name,
                outcome=outcome,
            )
        return outcome

    def _ingest_article(
        self,
        db: Session,
        source: ArticleSource,
        fetch_url: str,
        canonical_url: str,
        title_hint: str,
        outcome: IngestionOutcome,
    ) -> None:
        fetch_result = self.spider.fetch_article_html(fetch_url)
        if not fetch_result.ok or not fetch_result.html:
            outcome.failed_count += 1
            if fetch_result.error and not outcome.message:
                outcome.message = fetch_result.error
            return

        parsed = self.spider.parse_article_html(fetch_result.html, fetch_url)
        parsed_url = normalize_wechat_article_url(parsed.url or canonical_url)
        features = self.provider.extract_features(parsed.text)
        storage_path = article_storage_dir(
            self.settings.article_storage_path,
            source.name,
            parsed.publish_time,
            parsed.title,
        )
        saved_html = self.storage.save_webpage_with_resources(fetch_url, str(storage_path))

        existing = db.scalar(select(Article).where(Article.url == parsed_url))
        article = existing or Article(source_id=source.id, url=parsed_url)
        article.title = parsed.title or title_hint
        article.author = parsed.author
        article.publish_time = parsed.publish_time
        article.raw_html_path = saved_html
        article.raw_text = features.get("formatted_text") or parsed.text
        article.summary = features.get("summary") or parsed.summary
        article.topic_tags = features.get("topic_tags") or parsed.topic_tags
        article.entity_tags = features.get("entity_tags") or parsed.entity_tags
        article.content_type = features.get("content_type") or parsed.content_type
        article.core_claims = features.get("core_claims") or parsed.core_claims
        article.key_variables = features.get("key_variables") or parsed.key_variables
        article.catalysts = features.get("catalysts") or parsed.catalysts
        article.risks = features.get("risks") or parsed.risks
        article.style_tags = features.get("style_tags") or parsed.style_tags
        article.recommendation_reason = None

        metadata = dict(parsed.metadata)
        metadata["canonical_article_url"] = parsed_url
        metadata["fetch_url"] = fetch_url
        metadata["analysis_model"] = self.provider.name
        metadata["taxonomy_version"] = features.get("taxonomy_version") or TAXONOMY_VERSION
        metadata["analysis_features"] = features
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
                    embedding_model=self.provider.name,
                    content_hash=content_hash,
                    embedding=embedding,
                )
            )

        if existing:
            outcome.updated_count += 1
        else:
            outcome.imported_count += 1
        outcome.article_ids.append(article.id)
