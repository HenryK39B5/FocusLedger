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
    appmsg_token: str = ""
    session_us: str = ""
    scene: str = "124"
    username: str = ""
    raw_query: dict[str, str] | None = None


@dataclass
class WeChatArticleListItem:
    page_index: int
    local_time: str
    publish_time: str
    title: str
    cover: str
    raw_url: str
    url: str


@dataclass
class WeChatArticleListResult:
    items: list[WeChatArticleListItem]
    error: str | None = None
    ret_code: int | None = None
    raw_message: str | None = None
    failure_reason_category: str | None = None
    needs_refresh: bool = False


@dataclass
class WeChatCredentialValidationResult:
    valid: bool
    credential_status: str
    message: str
    error_code: str | None = None
    error_message: str | None = None
    needs_refresh: bool = False


class WeChatFuncs(BaseSpider):
    @staticmethod
    def _result_error(
        *,
        error: str,
        failure_reason_category: str,
        needs_refresh: bool = False,
        ret_code: int | None = None,
        raw_message: str | None = None,
    ) -> WeChatArticleListResult:
        return WeChatArticleListResult(
            items=[],
            error=error,
            ret_code=ret_code,
            raw_message=raw_message,
            failure_reason_category=failure_reason_category,
            needs_refresh=needs_refresh,
        )

    @staticmethod
    def _parse_query_preserve_plus(query: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for chunk in query.split("&"):
            if not chunk:
                continue
            if "=" in chunk:
                key, value = chunk.split("=", 1)
            else:
                key, value = chunk, ""
            result[parse.unquote(key)] = parse.unquote(value)
        return result

    def parse_token_link(self, token_url: str) -> WeChatTokenLink | None:
        parsed = parse.urlparse(token_url)
        query = self._parse_query_preserve_plus(parsed.query)
        try:
            return WeChatTokenLink(
                biz=query["__biz"],
                uin=query["uin"],
                key=query["key"],
                pass_ticket=query["pass_ticket"],
                appmsg_token=query.get("appmsg_token", ""),
                session_us=query.get("session_us", ""),
                scene=query.get("scene", "124"),
                username=query.get("username", ""),
                raw_query=query,
            )
        except KeyError:
            return None

    def _build_getmsg_url(self, token: WeChatTokenLink, offset: int) -> str:
        query_pairs = [
            ("action", "getmsg"),
            ("__biz", token.biz),
            ("f", "json"),
            ("offset", str(offset)),
            ("count", "10"),
            ("is_ok", "1"),
            ("scene", token.scene or "124"),
            ("uin", token.uin),
            ("key", token.key),
            ("pass_ticket", token.pass_ticket),
            ("wxtoken", token.raw_query.get("wxtoken", "") if token.raw_query else ""),
            ("appmsg_token", token.appmsg_token),
            ("x5", token.raw_query.get("x5", "0") if token.raw_query else "0"),
        ]
        if token.session_us:
            query_pairs.append(("session_us", token.session_us))
        if token.username:
            query_pairs.append(("username", token.username))
        return "https://mp.weixin.qq.com/mp/profile_ext?" + parse.urlencode(query_pairs)

    def fetch_article_list(
        self,
        token_url: str,
        page_start: int,
        page_end: int | None = None,
        since_days: int | None = None,
    ) -> list[WeChatArticleListItem]:
        return self.fetch_article_list_result(token_url, page_start, page_end, since_days).items

    def fetch_article_list_result(
        self,
        token_url: str,
        page_start: int,
        page_end: int | None = None,
        since_days: int | None = None,
    ) -> WeChatArticleListResult:
        token = self.parse_token_link(token_url)
        if not token:
            return self._result_error(
                error="无法解析来源链接中的关键参数。",
                failure_reason_category="invalid_token",
            )

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
            url = self._build_getmsg_url(token, offset)
            try:
                response = self.session.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    proxies={"http": None, "https": None},
                )
                if "general_msg_list" not in response.text:
                    raw_message = response.text[:500]
                    if '"errmsg":"no session"' in response.text or '"ret":-3' in response.text:
                        return self._result_error(
                            error="来源链接已失效，微信返回 no session，请重新刷新该来源的 profile_ext 凭据。",
                            failure_reason_category="no_session",
                            needs_refresh=True,
                            ret_code=-3,
                            raw_message=raw_message,
                        )
                    if '"home_page_list":[]' in response.text:
                        return self._result_error(
                            error="微信返回空主页列表，当前凭据很可能已经失效，请重新获取新的来源凭据。",
                            failure_reason_category="empty_response",
                            needs_refresh=True,
                            raw_message=raw_message,
                        )
                    return self._result_error(
                        error="未获取到可解析的公众号文章列表响应，请检查来源凭据是否仍然有效。",
                        failure_reason_category="empty_response",
                        raw_message=raw_message,
                    )

                payload = json.loads(response.text)
                msg_list = json.loads(payload["general_msg_list"]).get("list", [])
                for message in msg_list:
                    base = message.get("app_msg_ext_info", {})
                    publish_at = datetime.fromtimestamp(message["comm_msg_info"]["datetime"], tz=timezone.utc)
                    local_time = publish_at.astimezone(shanghai_tz).strftime("%Y-%m-%d %H:%M:%S")

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
                                publish_time=local_time,
                                title=base.get("title", "").strip(),
                                cover=base.get("cover", ""),
                                raw_url=raw_url,
                                url=normalize_wechat_article_url(raw_url),
                            )
                        )

                    for sub in base.get("multi_app_msg_item_list", []) or []:
                        sub_url = sub.get("content_url", "").replace("#wechat_redirect", "")
                        if not sub_url:
                            continue
                        raw_url = sub_url.replace("amp;", "")
                        items.append(
                            WeChatArticleListItem(
                                page_index=page + 1,
                                local_time=local_time,
                                publish_time=local_time,
                                title=sub.get("title", "").strip(),
                                cover=sub.get("cover", ""),
                                raw_url=raw_url,
                                url=normalize_wechat_article_url(raw_url),
                            )
                        )

                if stop_early:
                    break
                sleep_long()
            except Exception as exc:
                return self._result_error(
                    error=f"获取公众号文章列表失败：{exc}",
                    failure_reason_category="network_error",
                )

        if not items:
            return self._result_error(
                error="当前同步范围内没有获取到文章，请放宽时间范围或检查来源凭据是否仍然有效。",
                failure_reason_category="no_articles_in_range",
            )

        return WeChatArticleListResult(items=items)

    def verify_token_link(self, token_url: str) -> WeChatCredentialValidationResult:
        result = self.fetch_article_list_result(token_url, page_start=1, page_end=1, since_days=None)
        if result.error:
            if result.failure_reason_category in {"no_session", "empty_response"}:
                return WeChatCredentialValidationResult(
                    valid=False,
                    credential_status="refresh_required",
                    message=result.error,
                    error_code=result.failure_reason_category,
                    error_message=result.error,
                    needs_refresh=True,
                )
            if result.failure_reason_category == "invalid_token":
                return WeChatCredentialValidationResult(
                    valid=False,
                    credential_status="invalid",
                    message=result.error,
                    error_code=result.failure_reason_category,
                    error_message=result.error,
                )
            if result.failure_reason_category == "no_articles_in_range":
                return WeChatCredentialValidationResult(
                    valid=True,
                    credential_status="valid",
                    message="来源凭据验证通过，但当前探测范围内没有文章。",
                )
            return WeChatCredentialValidationResult(
                valid=False,
                credential_status="unknown",
                message=result.error,
                error_code=result.failure_reason_category,
                error_message=result.error,
            )

        return WeChatCredentialValidationResult(
            valid=True,
            credential_status="valid",
            message="来源凭据验证通过，可以继续同步。",
        )

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
            "__biz": token.biz,
            "appmsg_type": "9",
            "mid": mid,
            "sn": sn,
            "idx": idx,
            "scene": "0",
            "title": "",
            "ct": "",
            "abtest_cookie": "",
            "devicetype": "Windows",
            "version": "63090b19",
            "is_need_ticket": "0",
            "is_need_ad": "0",
            "comment_id": comment_id,
            "is_need_reward": "0",
            "both_ad": "0",
            "reward_uin_count": "0",
            "send_time": "",
            "msg_daily_idx": "1",
            "is_original_article": "0",
            "is_only_read": "0",
            "req_id": req_id,
            "pass_ticket": token.pass_ticket,
        }
        try:
            response = self.session.post(
                detail_url,
                headers=self.headers,
                data=data,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            return response.json()
        except Exception:
            return {}
