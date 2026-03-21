from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib import parse

from src.integrations.wechat_ingestion.core.base_spider import BaseSpider
from src.integrations.wechat_ingestion.utils.discovery import normalize_wechat_article_url
from src.integrations.wechat_ingestion.utils.tools import sleep_long


@dataclass
class WeChatTokenLink:
    biz: str
    uin: str
    key: str
    pass_ticket: str


@dataclass
class WeChatArticleListItem:
    page_index: int
    local_time: str
    publish_time: str
    title: str
    cover: str
    raw_url: str
    url: str


class WeChatFuncs(BaseSpider):
    def parse_token_link(self, token_url: str) -> WeChatTokenLink | None:
        parsed = parse.urlparse(token_url)
        query = parse.parse_qs(parsed.query)
        try:
            return WeChatTokenLink(
                biz=query["__biz"][0],
                uin=query["uin"][0],
                key=query["key"][0],
                pass_ticket=query["pass_ticket"][0],
            )
        except Exception:
            return None

    def fetch_article_list(
        self,
        token_url: str,
        page_start: int,
        page_end: int | None = None,
        since_days: int | None = None,
    ) -> list[WeChatArticleListItem]:
        token = self.parse_token_link(token_url)
        if not token:
            return []
        page_end = page_start if page_end is None else page_end
        items: list[WeChatArticleListItem] = []
        cutoff = None
        if since_days is not None and since_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        shanghai_tz = ZoneInfo("Asia/Shanghai")
        stop_early = False
        for page in range(page_start - 1, page_end):
            if stop_early:
                break
            offset = page * 10
            url = (
                "https://mp.weixin.qq.com/mp/profile_ext?action=getmsg"
                f"&__biz={token.biz}&f=json&offset={offset}&count=10&is_ok=1"
                f"&scene=124&uin={token.uin}&key={token.key}&pass_ticket={token.pass_ticket}"
                "&wxtoken=&appmsg_token=&x5=0&f=json"
            )
            try:
                response = self.session.get(url, headers=self.headers, timeout=self.timeout, verify=False)
                if "general_msg_list" not in response.text:
                    break
                payload = json.loads(response.text)
                msg_list = json.loads(payload["general_msg_list"]).get("list", [])
                for message in msg_list:
                    base = message.get("app_msg_ext_info", {})
                    publish_at = datetime.fromtimestamp(message["comm_msg_info"]["datetime"], tz=timezone.utc)
                    local_time = publish_at.astimezone(shanghai_tz).strftime("%Y-%m-%d %H:%M:%S")
                    publish_time = local_time
                    if cutoff and publish_at < cutoff:
                        stop_early = True
                        break
                    article_url = base.get("content_url", "").replace("#wechat_redirect", "")
                    if article_url:
                        raw_url = article_url.replace("amp;", "")
                        items.append(
                            WeChatArticleListItem(
                                page_index=page + 1,
                                local_time=local_time,
                                publish_time=publish_time,
                                title=base.get("title", "").strip(),
                                cover=base.get("cover", ""),
                                raw_url=raw_url,
                                url=normalize_wechat_article_url(raw_url),
                            )
                        )
                    for sub in base.get("multi_app_msg_item_list", []) or []:
                        sub_url = sub.get("content_url", "").replace("#wechat_redirect", "")
                        if sub_url:
                            raw_url = sub_url.replace("amp;", "")
                            items.append(
                                WeChatArticleListItem(
                                    page_index=page + 1,
                                    local_time=local_time,
                                    publish_time=publish_time,
                                    title=sub.get("title", "").strip(),
                                    cover=sub.get("cover", ""),
                                    raw_url=raw_url,
                                    url=normalize_wechat_article_url(raw_url),
                                )
                            )
                if stop_early:
                    break
                sleep_long()
            except Exception:
                break
        return items

    def fetch_article_metrics(self, token_url: str, article_url: str, html: str) -> dict:
        token = self.parse_token_link(token_url)
        if not token:
            return {}
        if "mid=" not in article_url or "sn=" not in article_url or "idx=" not in article_url:
            return {}
        mid = article_url.split("mid=")[1].split("&")[0]
        sn = article_url.split("sn=")[1].split("&")[0]
        idx = article_url.split("idx=")[1].split("&")[0]
        comment_id = ""
        req_id = ""
        comment_match = re.search(r"var comment_id = '(.*?)'", html)
        if comment_match:
            comment_id = comment_match.group(1)
        req_match = re.search(r"var req_id = ([^;]+);", html)
        if req_match:
            req_id = req_match.group(1).strip("'\"")
        detail_url = (
            "https://mp.weixin.qq.com/mp/getappmsgext?f=json&fasttmplajax=1"
            f"&uin={token.uin}&key={token.key}&pass_ticket={token.pass_ticket}&__biz={token.biz}"
        )
        data = {
            "r": "0.123456789",
            "sn": sn,
            "mid": mid,
            "idx": idx,
            "req_id": req_id,
            "title": "",
            "comment_id": comment_id,
            "appmsg_type": "9",
            "__biz": token.biz,
            "pass_ticket": token.pass_ticket,
            "scene": "38",
            "is_only_read": "1",
        }
        try:
            response = self.session.post(detail_url, data=data, headers=self.headers, timeout=self.timeout, verify=False)
            return response.json()
        except Exception:
            return {}
