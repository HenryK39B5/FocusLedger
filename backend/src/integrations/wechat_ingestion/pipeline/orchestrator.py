from __future__ import annotations

from collections.abc import Callable
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
from src.models import Article, ArticleEmbedding, ArticleSource


ProgressCallback = Callable[[dict], None]


@dataclass
class IngestionOutcome:
    imported_count: int = 0
    updated_count: int = 0
    failed_count: int = 0
    article_ids: list[str] | None = None
    message: str = ""
    needs_refresh: bool = False
    credential_status_after_run: str = "unknown"
    failure_reason_category: str | None = None
    total_candidates: int = 0

    def __post_init__(self) -> None:
        if self.article_ids is None:
            self.article_ids = []


class WechatIngestionPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.spider = BaseSpider(timeout=settings.request_timeout_seconds, verify_ssl=settings.wechat_verify_ssl)
        self.wechat = WeChatFuncs(timeout=settings.request_timeout_seconds, verify_ssl=settings.wechat_verify_ssl)
        self.storage = SaveWebpageToHtml(verify_ssl=settings.wechat_verify_ssl)
        self.provider = build_provider(settings)

    def run(
        self,
        db: Session,
        source: ArticleSource,
        page_start: int = 1,
        page_end: int = 20,
        since_days: int | None = 7,
        date_from: str | None = None,
        date_to: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> IngestionOutcome:
        outcome = IngestionOutcome(message="采集完成", credential_status_after_run=source.credential_status)
        credential_link = source.credential.raw_link if source.credential else ""

        def emit(**event: dict) -> None:
            if progress_callback:
                progress_callback(event)

        emit(stage="verifying_credential", message="正在验证来源凭据。")

        if "mp.weixin.qq.com" not in credential_link or "profile_ext" not in credential_link:
            outcome.failed_count = 1
            outcome.message = "当前来源缺少可用的公众号历史消息凭据，请先更新来源链接。"
            outcome.needs_refresh = True
            outcome.failure_reason_category = "invalid_token"
            outcome.credential_status_after_run = "refresh_required"
            emit(stage="verifying_credential", failed_count=1, message=outcome.message)
            return outcome

        token = self.wechat.parse_token_link(credential_link)
        if not token:
            outcome.failed_count = 1
            outcome.message = "当前凭据不是可用的公众号历史消息入口，请重新粘贴完整的 profile_ext 链接。"
            outcome.failure_reason_category = "invalid_token"
            outcome.credential_status_after_run = "invalid"
            emit(stage="verifying_credential", failed_count=1, message=outcome.message)
            return outcome

        article_list_result = self.wechat.fetch_article_list_result(
            credential_link,
            page_start,
            page_end,
            since_days=since_days,
            date_from=date_from,
            date_to=date_to,
        )
        if article_list_result.error:
            outcome.failed_count = 1
            outcome.message = article_list_result.error
            outcome.needs_refresh = article_list_result.needs_refresh
            outcome.failure_reason_category = article_list_result.failure_reason_category
            if article_list_result.failure_reason_category in {"no_session", "empty_response"}:
                outcome.credential_status_after_run = "refresh_required"
            elif article_list_result.failure_reason_category == "invalid_token":
                outcome.credential_status_after_run = "invalid"
            elif article_list_result.failure_reason_category == "no_articles_in_range":
                outcome.credential_status_after_run = "valid"
            emit(
                stage="fetching_article_list",
                failed_count=1,
                total_candidates=0,
                message=article_list_result.error,
            )
            return outcome

        items = article_list_result.items
        outcome.total_candidates = len(items)
        emit(
            stage="fetching_article_list",
            total_candidates=len(items),
            message=f"已获取候选文章 {len(items)} 篇，开始逐篇处理。",
        )

        seen_urls: set[str] = set()
        total_candidates = len(items)
        processed_count = 0
        for item in items:
            canonical_url = normalize_wechat_article_url(item.url)
            if canonical_url in seen_urls:
                continue
            seen_urls.add(canonical_url)
            emit(
                stage="fetching_article_html",
                article_title=item.title,
                article_url=canonical_url,
                processed_count=processed_count,
                imported_count=outcome.imported_count,
                updated_count=outcome.updated_count,
                failed_count=outcome.failed_count,
                total_candidates=total_candidates,
                message=f"正在处理《{item.title or '未命名文章'}》。",
            )
            self._ingest_article(
                db=db,
                source=source,
                fetch_url=item.raw_url or item.url,
                canonical_url=canonical_url,
                title_hint=item.title,
                outcome=outcome,
                progress_callback=progress_callback,
            )
            processed_count += 1
            emit(
                stage="saving_article",
                article_title=item.title,
                article_url=canonical_url,
                processed_count=processed_count,
                imported_count=outcome.imported_count,
                updated_count=outcome.updated_count,
                failed_count=outcome.failed_count,
                total_candidates=total_candidates,
                message=f"已完成 {processed_count}/{total_candidates} 篇文章处理。",
            )

        if outcome.imported_count == 0 and outcome.updated_count == 0 and outcome.failed_count == 0:
            outcome.message = "当前同步范围内没有新增或更新文章。"
            outcome.failure_reason_category = "no_articles_in_range"
        else:
            outcome.credential_status_after_run = "valid"

        emit(
            stage="finalizing",
            processed_count=processed_count,
            imported_count=outcome.imported_count,
            updated_count=outcome.updated_count,
            failed_count=outcome.failed_count,
            total_candidates=total_candidates,
            message=outcome.message,
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
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        def emit(**event: dict) -> None:
            if progress_callback:
                progress_callback(event)

        fetch_result = self.spider.fetch_article_html(fetch_url)
        if not fetch_result.ok or not fetch_result.html:
            outcome.failed_count += 1
            if fetch_result.error and not outcome.message:
                outcome.message = fetch_result.error
                if "验证码" in fetch_result.error or "拦截" in fetch_result.error:
                    outcome.failure_reason_category = "captcha_or_blocked"
                else:
                    outcome.failure_reason_category = "network_error"
            emit(stage="fetching_article_html", failed_count=outcome.failed_count, message=fetch_result.error or "获取正文失败。")
            return

        emit(stage="parsing_article", article_title=title_hint, article_url=canonical_url, message="正文获取成功，开始解析。")
        parsed = self.spider.parse_article_html(fetch_result.html, fetch_url)
        parsed_url = normalize_wechat_article_url(parsed.url or canonical_url)
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

        if existing:
            outcome.updated_count += 1
        else:
            outcome.imported_count += 1
        outcome.article_ids.append(article.id)
        db.flush()
