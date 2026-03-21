from __future__ import annotations

from dataclasses import dataclass

import requests

from src.integrations.wechat_ingestion.utils.tools import sleep_short
from src.integrations.wechat_ingestion.utils.detection import is_wechat_captcha_page
from src.parsers.wechat import ParsedWechatArticle, parse_wechat_html


@dataclass
class FetchResult:
    ok: bool
    html: str | None = None
    url: str | None = None
    error: str | None = None


class BaseSpider:
    def __init__(self, timeout: int = 20):
        self.session = requests.Session()
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

    def fetch_article_html(self, url: str) -> FetchResult:
        try:
            response = self.session.get(url, headers=self.headers, timeout=self.timeout, verify=False)
            sleep_short()
            if response.ok and response.text:
                if is_wechat_captcha_page(response.text, response.url):
                    return FetchResult(
                        ok=False,
                        error=(
                            "微信返回了验证码/拦截页，未获取到正文。"
                            "如果你要测试真实公众号文章，需要提供已登录态的浏览器 Cookie，"
                            "或者使用历史消息页 token URL。"
                        ),
                    )
                return FetchResult(ok=True, html=response.text, url=str(response.url))
            return FetchResult(ok=False, error=f"HTTP {response.status_code}")
        except Exception as exc:  # pragma: no cover - network path
            return FetchResult(ok=False, error=str(exc))

    def parse_article_html(self, html: str, source_url: str) -> ParsedWechatArticle:
        return parse_wechat_html(html, source_url)
