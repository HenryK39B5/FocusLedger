from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from src.integrations.wechat_ingestion.utils.discovery import normalize_wechat_article_url, resolve_public_home_link

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


@dataclass
class ParsedWechatArticle:
    title: str
    author: str | None
    publish_time: str | None
    url: str
    source_name: str | None
    html: str
    text: str
    summary: str
    topic_tags: list[str] = field(default_factory=list)
    entity_tags: list[str] = field(default_factory=list)
    content_type: str = "深度研究"
    core_claims: list[str] = field(default_factory=list)
    key_variables: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    style_tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _extract_source_name(soup: BeautifulSoup) -> str | None:
    candidates = [
        soup.select_one(".wx_follow_nickname"),
        soup.select_one("#js_name"),
        soup.select_one('[aria-labelledby="js_wx_follow_nickname"]'),
    ]
    for node in candidates:
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return None


def _normalize_block_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_article_text(soup: BeautifulSoup) -> str:
    content_node = soup.select_one("#js_content")
    text_source = content_node or soup.body or soup

    for selector in ("script", "style", "noscript", "iframe"):
        for node in list(text_source.select(selector)):
            node.decompose()

    blocks: list[str] = []
    seen: set[str] = set()
    block_selectors = ("p", "section", "blockquote", "li", "h1", "h2", "h3", "h4")
    nodes = text_source.find_all(block_selectors)
    if not nodes:
        nodes = [text_source]

    for node in nodes:
        for br in node.find_all("br"):
            br.replace_with("\n")
        cleaned = _normalize_block_text(node.get_text("\n", strip=True))
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        blocks.append(cleaned)

    return "\n\n".join(blocks)


def parse_wechat_html(html: str, source_url: str) -> ParsedWechatArticle:
    soup = BeautifulSoup(html, "lxml")

    title = soup.find("meta", property="og:title")
    title_text = title.get("content", "").strip() if title else "未命名文章"

    author = soup.find("meta", attrs={"name": "author"})
    author_text = author.get("content", "").strip() if author else None

    html_url = soup.find("meta", property="og:url")
    raw_article_url = html_url.get("content", source_url).strip() if html_url else source_url
    article_url = normalize_wechat_article_url(raw_article_url)

    text = _extract_article_text(soup)
    summary = text[:180] + ("..." if len(text) > 180 else "")

    publish_time = None
    create_time_match = re.search(r"create_time:\s*['\"]([^'\"]+)['\"]", html)
    if not create_time_match:
        create_time_match = re.search(r"create_time:\s*JsDecode\('([^']+)'\)", html)
    if create_time_match:
        raw_publish_time = create_time_match.group(1).strip()
        if raw_publish_time.isdigit():
            timestamp = int(raw_publish_time)
            if len(raw_publish_time) >= 13:
                timestamp = int(raw_publish_time[:10])
            publish_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(SHANGHAI_TZ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            publish_time = raw_publish_time

    source_name = _extract_source_name(soup)
    biz, home_link = resolve_public_home_link(source_url, html)

    topic_tokens = sorted({token for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]+", text) if len(token) > 1})[:8]
    metadata = {
        "title": title_text,
        "author": author_text,
        "article_url": article_url,
        "raw_article_url": raw_article_url,
        "source_url": source_url,
        "biz": biz,
        "public_home_link": home_link,
    }

    return ParsedWechatArticle(
        title=title_text,
        author=author_text,
        publish_time=publish_time,
        url=article_url,
        source_name=source_name,
        html=html,
        text=text,
        summary=summary,
        topic_tags=topic_tokens,
        entity_tags=topic_tokens[:5],
        content_type="深度研究" if len(text) > 1200 else "快讯",
        core_claims=[text[:80]] if text else [],
        key_variables=topic_tokens[:4],
        catalysts=topic_tokens[4:6],
        risks=topic_tokens[6:8],
        style_tags=["style/结构化", "style/快讯"] if len(text) <= 1200 else ["style/结构化", "style/深度研究"],
        metadata=metadata,
    )
