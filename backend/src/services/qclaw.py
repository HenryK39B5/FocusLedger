from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.integrations.wechat_ingestion.utils.discovery import normalize_wechat_article_url
from src.models import Article
from src.schemas.qclaw import QClawDailyReportArticleLinkRead, QClawDailyReportRead
from src.services.reports import DailyReportService


def _truncate(text: str, limit: int) -> str:
    compact = " ".join(text.split()).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


class QClawReportService:
    def __init__(self) -> None:
        self.daily_report_service = DailyReportService()

    def build_daily_report_reply(
        self,
        db: Session,
        *,
        report_date: str | None,
        source_id: str | None,
        source_group: str | None,
        limit: int,
        style: str = "brief",
    ) -> QClawDailyReportRead:
        report = self.daily_report_service.build_daily_report(
            db,
            report_date=report_date,
            source_id=source_id,
            source_group=source_group,
            limit=limit,
        )
        matched_articles = int(report.stats.get("matched_articles", 0) or 0)
        selected_articles = int(report.stats.get("selected_articles", 0) or 0)

        if matched_articles <= 0:
            target = source_group or "全部来源"
            return QClawDailyReportRead(
                ok=False,
                date=report.date,
                title=f"{report.date} 日报",
                reply_text=f"{report.date} 没有匹配到文章，范围：{target}。请先同步来源，或换一个日期再试。",
                report_markdown=None,
                overview=None,
                matched_articles=0,
                selected_articles=0,
                source_group=report.source_group,
                source_id=report.source_id,
                article_links=[],
            )

        article_ids = [article.id for article in report.articles]
        article_rows = list(db.scalars(select(Article).where(Article.id.in_(article_ids))).all()) if article_ids else []
        article_map = {article.id: article for article in article_rows}
        article_links = [
            QClawDailyReportArticleLinkRead(
                id=article.id,
                title=article.title,
                url=normalize_wechat_article_url(article.url),
                source_name=article.source.name if article.source else "",
            )
            for article_id in article_ids
            if (article := article_map.get(article_id)) is not None
        ]

        lines = [report.title]
        if report.overview:
            lines.extend(["", _truncate(report.overview, 110 if style == "brief" else 140)])

        section_limit = 2 if style == "brief" else 4
        bullet_limit = 2 if style == "brief" else 3
        bullet_length = 52 if style == "brief" else 80

        for index, section in enumerate(report.sections[:section_limit], start=1):
            lines.extend(["", f"{index}. {section.title}"])
            if style != "brief" and section.summary:
                lines.append(_truncate(section.summary, 80))
            for bullet in section.bullets[:bullet_limit]:
                lines.append(f"- {_truncate(bullet, bullet_length)}")

        if report.follow_ups:
            lines.extend(["", "后续关注"])
            for item in report.follow_ups[: (2 if style == "brief" else 3)]:
                lines.append(f"- {_truncate(item, 48 if style == 'brief' else 60)}")

        if style != "brief" and article_links:
            lines.extend(["", "原文链接"])
            for link in article_links[:3]:
                lines.append(f"- {link.source_name} | {link.title}")
                lines.append(f"  {link.url}")

        if style == "brief":
            lines.extend(
                [
                    "",
                    f"覆盖文章 {matched_articles} 篇，纳入日报 {selected_articles} 篇。",
                    "如需原文链接或详细版，可继续回复：详细版。",
                ]
            )

        return QClawDailyReportRead(
            ok=True,
            date=report.date,
            title=report.title,
            reply_text="\n".join(lines).strip(),
            report_markdown=report.report_markdown,
            overview=report.overview,
            matched_articles=matched_articles,
            selected_articles=selected_articles,
            source_group=report.source_group,
            source_id=report.source_id,
            article_links=article_links,
        )
