from __future__ import annotations

from collections import Counter
from datetime import date as date_type, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.integrations.wechat_ingestion.utils.discovery import normalize_wechat_article_url
from src.llm.providers import build_provider
from src.models import Article, ArticleSource
from src.schemas.reports import DailyReportArticleRead, DailyReportRead, DailyReportSectionRead
from src.services.articles import normalize_publish_time, parse_publish_datetime
from src.services.sources import normalize_group_path

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def _parse_datetime(value: str | None) -> datetime | None:
    return parse_publish_datetime(value)


def _to_local_date(article: Article) -> date_type:
    parsed_publish = _parse_datetime(article.publish_time)
    if parsed_publish is not None:
        aware = parsed_publish if parsed_publish.tzinfo else parsed_publish.replace(tzinfo=timezone.utc)
        return aware.astimezone(SHANGHAI_TZ).date()
    created = article.created_at
    aware_created = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
    return aware_created.astimezone(SHANGHAI_TZ).date()


def _matches_group(article_group: str | None, target_group: str | None) -> bool:
    if not target_group:
        return True
    normalized_target = normalize_group_path(target_group)
    normalized_group = normalize_group_path(article_group)
    if not normalized_target:
        return True
    if not normalized_group:
        return False
    return normalized_group == normalized_target or normalized_group.startswith(f"{normalized_target}/")


def _importance_score(article: Article) -> float:
    summary_length = len(article.summary or article.raw_text or "")
    topic_count = len(article.topic_tags or [])
    entity_count = len(article.entity_tags or [])
    style_count = len(article.style_tags or [])
    content_boost = {
        "深度研究": 0.22,
        "公告解读": 0.20,
        "数据解读": 0.18,
        "访谈": 0.15,
        "复盘": 0.12,
        "观点": 0.10,
        "快讯": 0.08,
        "新闻": 0.06,
    }.get(article.content_type or "", 0.05)
    text_boost = min(summary_length / 2400.0, 1.0) * 0.25
    signal_boost = min(topic_count / 6.0, 1.0) * 0.2 + min(entity_count / 6.0, 1.0) * 0.15 + min(style_count / 4.0, 1.0) * 0.08
    return round(text_boost + signal_boost + content_boost, 4)


def _build_article_read(article: Article, importance_score: float) -> DailyReportArticleRead:
    return DailyReportArticleRead(
        id=article.id,
        title=article.title,
        source_name=article.source.name if article.source else "",
        source_group=article.source.source_group if article.source else None,
        source_tags=article.source.tags if article.source else [],
        publish_time=normalize_publish_time(article.publish_time, article.created_at),
        summary=article.summary,
        topic_tags=article.topic_tags,
        entity_tags=article.entity_tags,
        style_tags=article.style_tags,
        content_type=article.content_type,
        importance_score=importance_score,
    )


def _build_markdown(title: str, overview: str, sections: list[DailyReportSectionRead], follow_ups: list[str]) -> str:
    lines = [f"# {title}", ""]
    if overview:
        lines.extend(["## 概览", overview, ""])
    for section in sections:
        lines.append(f"## {section.title}")
        if section.summary:
            lines.append(section.summary)
        for bullet in section.bullets:
            lines.append(f"- {bullet}")
        lines.append("")
    if follow_ups:
        lines.append("## 后续关注")
        for item in follow_ups:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).strip()


class DailyReportService:
    def build_daily_report(
        self,
        db: Session,
        report_date: str | date_type | None = None,
        source_id: str | None = None,
        source_group: str | None = None,
        limit: int = 20,
    ) -> DailyReportRead:
        settings = get_settings()
        provider = build_provider(settings)
        target_date = self._parse_report_date(report_date)

        stmt = select(Article).join(ArticleSource, Article.source_id == ArticleSource.id).order_by(desc(Article.created_at))
        if source_id:
            stmt = stmt.where(Article.source_id == source_id)
        articles = list(db.scalars(stmt.limit(max(limit * 25, 300))).all())

        filtered = [
            article
            for article in articles
            if _to_local_date(article) == target_date
            and _matches_group(article.source.source_group if article.source else None, source_group)
        ]
        filtered.sort(key=lambda article: (_importance_score(article), article.created_at), reverse=True)

        selected = filtered[: max(limit, 1)]
        selected_reads = [_build_article_read(article, _importance_score(article)) for article in selected]

        group_buckets: dict[str, dict[str, object]] = {}
        for article in selected:
            group_key = article.source.source_group if article.source and article.source.source_group else "未分组"
            bucket = group_buckets.setdefault(
                group_key,
                {
                    "group": group_key,
                    "source_count": 0,
                    "article_count": 0,
                    "source_names": set(),
                    "source_tags": set(),
                    "articles": [],
                },
            )
            bucket["article_count"] = int(bucket["article_count"]) + 1
            bucket["source_names"].add(article.source.name if article.source else "")
            if article.source:
                bucket["source_tags"].update(article.source.tags or [])
            bucket["articles"].append(
                {
                    "id": article.id,
                    "title": article.title,
                    "source_name": article.source.name if article.source else "",
                    "summary": article.summary or article.raw_text or "",
                    "topic_tags": article.topic_tags,
                    "entity_tags": article.entity_tags,
                    "style_tags": article.style_tags,
                    "publish_time": normalize_publish_time(article.publish_time, article.created_at),
                    "content_type": article.content_type,
                }
            )

        for bucket in group_buckets.values():
            source_names = {name for name in bucket["source_names"] if name}
            bucket["source_count"] = len(source_names)
            bucket["source_names"] = sorted(source_names)
            bucket["source_tags"] = sorted({tag for tag in bucket["source_tags"] if tag})
            bucket["articles"] = bucket["articles"][: max(3, limit)]

        grouped_context = sorted(group_buckets.values(), key=lambda item: (-int(item["article_count"]), str(item["group"])))
        top_topic_tags = Counter(tag for article in selected for tag in (article.topic_tags or []))
        top_entities = Counter(tag for article in selected for tag in (article.entity_tags or []))

        context = {
            "date": target_date.isoformat(),
            "source_id": source_id,
            "source_group": normalize_group_path(source_group),
            "total_articles": len(filtered),
            "selected_articles": len(selected),
            "source_groups": grouped_context,
            "top_topic_tags": top_topic_tags.most_common(12),
            "top_entities": top_entities.most_common(12),
            "articles": [
                {
                    "id": article.id,
                    "title": article.title,
                    "source_name": article.source.name if article.source else "",
                    "source_group": article.source.source_group if article.source else None,
                    "source_tags": article.source.tags if article.source else [],
                    "publish_time": normalize_publish_time(article.publish_time, article.created_at),
                    "summary": article.summary or article.raw_text or "",
                    "topic_tags": article.topic_tags,
                    "entity_tags": article.entity_tags,
                    "style_tags": article.style_tags,
                    "content_type": article.content_type,
                    "importance_score": _importance_score(article),
                    "url": normalize_wechat_article_url(article.url),
                }
                for article in selected
            ],
        }

        generated = provider.generate_daily_report(context)
        title = str(generated.get("title") or f"{target_date.isoformat()} 公众号日报")
        overview = str(generated.get("overview") or "").strip() or None

        sections: list[DailyReportSectionRead] = []
        for section in generated.get("sections", []) or []:
            if not isinstance(section, dict):
                continue
            sections.append(
                DailyReportSectionRead(
                    title=str(section.get("title") or "未命名分区"),
                    summary=str(section.get("summary") or "").strip() or None,
                    bullets=[str(item).strip() for item in section.get("bullets", []) if str(item).strip()],
                    article_ids=[str(item).strip() for item in section.get("article_ids", []) if str(item).strip()],
                )
            )

        follow_ups = [str(item).strip() for item in generated.get("follow_ups", []) if str(item).strip()]
        markdown = str(generated.get("report_markdown") or "").strip()
        if not markdown:
            markdown = _build_markdown(title, overview or "", sections, follow_ups)

        return DailyReportRead(
            date=target_date.isoformat(),
            title=title,
            overview=overview,
            report_markdown=markdown,
            follow_ups=follow_ups,
            sections=sections,
            articles=selected_reads,
            stats={
                "matched_articles": len(filtered),
                "selected_articles": len(selected),
                "source_group_count": len(grouped_context),
                "top_topic_tags": top_topic_tags.most_common(10),
                "top_entities": top_entities.most_common(10),
            },
            generated_at=datetime.now(timezone.utc),
            source_id=source_id,
            source_group=normalize_group_path(source_group),
        )

    def _parse_report_date(self, value: str | date_type | None) -> date_type:
        if value is None:
            return datetime.now(SHANGHAI_TZ).date()
        if isinstance(value, date_type):
            return value
        raw = value.strip()
        if not raw:
            return datetime.now(SHANGHAI_TZ).date()
        return date_type.fromisoformat(raw)
