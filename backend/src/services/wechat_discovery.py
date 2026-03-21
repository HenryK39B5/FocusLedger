from __future__ import annotations

from src.core.config import Settings
from src.integrations.wechat_ingestion.core.base_spider import BaseSpider
from src.integrations.wechat_ingestion.utils.discovery import resolve_public_home_link
from src.schemas.wechat import WechatHomeLinkResolveResponse


class WeChatDiscoveryService:
    def __init__(self, settings: Settings):
        self.spider = BaseSpider(timeout=settings.request_timeout_seconds)

    def resolve_home_link(self, article_url: str) -> WechatHomeLinkResolveResponse:
        biz, home_link = resolve_public_home_link(article_url)
        if home_link:
            article_title = None
            source_name = None
            fetch_result = self.spider.fetch_article_html(article_url)
            if fetch_result.ok and fetch_result.html:
                parsed = self.spider.parse_article_html(fetch_result.html, article_url)
                article_title = parsed.title
                source_name = parsed.source_name
            return WechatHomeLinkResolveResponse(
                article_url=article_url,
                article_title=article_title,
                source_name=source_name,
                biz=biz,
                public_home_link=home_link,
                resolved=True,
                message="已从链接参数中提取公众号主页链接",
            )

        fetch_result = self.spider.fetch_article_html(article_url)
        if not fetch_result.ok or not fetch_result.html:
            return WechatHomeLinkResolveResponse(
                article_url=article_url,
                resolved=False,
                message=fetch_result.error or "无法获取文章页面，可能被微信验证码拦截",
            )

        biz, home_link = resolve_public_home_link(article_url, fetch_result.html)
        if not home_link:
            return WechatHomeLinkResolveResponse(
                article_url=article_url,
                resolved=False,
                message="未能从文章页解析出 __biz，请使用微信PC / Fiddler 打开文章后再重试",
            )

        parsed = self.spider.parse_article_html(fetch_result.html, article_url)
        return WechatHomeLinkResolveResponse(
            article_url=article_url,
            article_title=parsed.title,
            source_name=parsed.source_name,
            biz=biz,
            public_home_link=home_link,
            resolved=True,
            message="已从文章页解析出公众号主页链接",
        )
