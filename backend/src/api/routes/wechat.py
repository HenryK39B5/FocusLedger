from __future__ import annotations

from fastapi import APIRouter

from src.core.config import get_settings
from src.schemas.wechat import WechatHomeLinkResolveRequest, WechatHomeLinkResolveResponse
from src.services.wechat_discovery import WeChatDiscoveryService

router = APIRouter(prefix="/wechat", tags=["wechat"])


@router.post("/resolve-home", response_model=WechatHomeLinkResolveResponse)
def resolve_home_link(payload: WechatHomeLinkResolveRequest):
    service = WeChatDiscoveryService(get_settings())
    return service.resolve_home_link(payload.article_url)
