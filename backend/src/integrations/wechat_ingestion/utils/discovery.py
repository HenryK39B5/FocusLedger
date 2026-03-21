from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def extract_biz_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    biz = query.get("__biz", [None])[0]
    return biz or None


def extract_biz_from_html(html: str) -> str | None:
    match = re.search(r"biz:\s*[\"']([^\"']+)[\"']", html)
    return match.group(1) if match else None


def build_public_home_link(biz: str) -> str:
    return f"https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={biz}&scene=124#wechat_redirect"


def normalize_wechat_article_url(url: str) -> str:
    cleaned = url.replace("amp;", "").split("#")[0]
    parsed = urlparse(cleaned)
    query = parse_qs(parsed.query)
    keep_order = ["__biz", "mid", "idx", "sn"]
    pairs: list[tuple[str, str]] = []
    for key in keep_order:
        value = query.get(key, [None])[0]
        if value:
            pairs.append((key, value))
    if not pairs:
        return cleaned
    return urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc or "mp.weixin.qq.com",
            parsed.path or "/",
            "",
            urlencode(pairs),
            "",
        )
    )


def resolve_public_home_link(url: str, html: str | None = None) -> tuple[str | None, str | None]:
    biz = extract_biz_from_url(url)
    if not biz and html:
        biz = extract_biz_from_html(html)
    if not biz:
        return None, None
    return biz, build_public_home_link(biz)
