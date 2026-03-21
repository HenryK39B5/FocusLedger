from __future__ import annotations

from src.schemas.common import SchemaBase


class WechatHomeLinkResolveRequest(SchemaBase):
    article_url: str


class WechatHomeLinkResolveResponse(SchemaBase):
    article_url: str
    article_title: str | None = None
    source_name: str | None = None
    biz: str | None = None
    public_home_link: str | None = None
    resolved: bool = False
    message: str | None = None

