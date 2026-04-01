from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

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


def _normalize_line(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_noise_text(text: str) -> bool:
    normalized = _normalize_line(text)
    if not normalized:
        return True
    noise_fragments = (
        "微信扫一扫",
        "收藏",
        "点赞",
        "在看",
        "分享",
        "写留言",
        "继续滑动看下一个",
        "轻触阅读原文",
        "预览时标签不可点",
        "喜欢此内容的人还喜欢",
    )
    return any(fragment in normalized for fragment in noise_fragments)


def _prepare_content_node(content_node: Tag) -> Tag:
    removable_selectors = (
        "script",
        "style",
        "noscript",
        "iframe",
        ".weui-mask",
        ".js_img_placeholder",
        ".img_loading",
        ".wx_profile_card_inner",
        ".wx_profile_card",
        ".original_area_primary",
        ".mpda_bottom_container",
        ".js_product_loop_content",
        ".js_insert_local_video",
        ".js_ad_link",
        ".js_related_article_container",
        ".wx_tap_link",
        ".reward_area",
        ".js_unread_area",
        ".js_share_msg",
    )
    for selector in removable_selectors:
        for node in list(content_node.select(selector)):
            node.decompose()

    for node in list(content_node.find_all(attrs={"style": re.compile(r"display\s*:\s*none", re.I)})):
        node.decompose()
    return content_node


def _collect_block_text(node: Tag) -> list[str]:
    blocks: list[str] = []
    target_tags = {"h1", "h2", "h3", "h4", "p", "section", "blockquote", "li", "pre"}
    for candidate in node.descendants:
        if not isinstance(candidate, Tag):
            continue
        if candidate.name not in target_tags:
            continue
        for br in candidate.find_all("br"):
            br.replace_with("\n")
        text = candidate.get_text("\n", strip=True)
        text = _normalize_line(text)
        if not text or _is_noise_text(text):
            continue
        blocks.append(text)
    return blocks


def _extract_article_text(soup: BeautifulSoup) -> str:
    content_node = soup.select_one("#js_content")
    if content_node is None:
        text_source = soup.body or soup
        for selector in ("script", "style", "noscript", "iframe"):
            for node in list(text_source.select(selector)):
                node.decompose()
        text = text_source.get_text("\n", strip=True)
        return _normalize_line(re.sub(r"\n{2,}", "\n\n", text))

    content_node = _prepare_content_node(content_node)
    blocks = _collect_block_text(content_node)
    if not blocks:
        text = content_node.get_text("\n", strip=True)
        return _normalize_line(re.sub(r"\n{2,}", "\n\n", text))

    merged: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        if block in seen:
            continue
        seen.add(block)
        merged.append(block)
    return "\n\n".join(merged)


def _extract_publish_time(html: str) -> str | None:
    create_time_match = re.search(r"create_time:\s*['\"]([^'\"]+)['\"]", html)
    if not create_time_match:
        create_time_match = re.search(r"create_time:\s*JsDecode\('([^']+)'\)", html)
    if not create_time_match:
        return None

    raw_publish_time = create_time_match.group(1).strip()
    if raw_publish_time.isdigit():
        timestamp = int(raw_publish_time)
        if len(raw_publish_time) >= 13:
            timestamp = int(raw_publish_time[:10])
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(SHANGHAI_TZ).strftime("%Y-%m-%d %H:%M:%S")
    return raw_publish_time


def parse_wechat_html(html: str, source_url: str) -> ParsedWechatArticle:
    soup = BeautifulSoup(html, "lxml")

    title_meta = soup.find("meta", property="og:title")
    title_text = title_meta.get("content", "").strip() if title_meta else "未命名文章"

    author_meta = soup.find("meta", attrs={"name": "author"})
    author_text = author_meta.get("content", "").strip() if author_meta else None

    html_url = soup.find("meta", property="og:url")
    raw_article_url = html_url.get("content", source_url).strip() if html_url else source_url
    article_url = normalize_wechat_article_url(raw_article_url)

    text = _extract_article_text(soup)
    summary = text[:180] + ("..." if len(text) > 180 else "")
    publish_time = _extract_publish_time(html)
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

    is_long_form = len(text) > 1200
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
        content_type="深度研究" if is_long_form else "快讯",
        core_claims=[text[:80]] if text else [],
        key_variables=topic_tokens[:4],
        catalysts=topic_tokens[4:6],
        risks=topic_tokens[6:8],
        style_tags=["style/结构化", "style/深度研究"] if is_long_form else ["style/结构化", "style/快讯"],
        metadata=metadata,
    )
