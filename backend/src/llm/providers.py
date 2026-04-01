from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

from src.core.config import Settings
from src.llm.taxonomy import (
    CONTENT_TYPE_SET,
    STYLE_TAG_SET,
    TAXONOMY_VERSION,
    TOPIC_TAG_SET,
    extract_entity_tags,
    normalize_tag_items,
    suggest_catalysts,
    suggest_content_type,
    suggest_core_claims,
    suggest_key_variables,
    suggest_risks,
    suggest_style_tags,
    suggest_topic_tags,
    taxonomy_prompt_block,
)

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    return re.sub(r"\r\n?", "\n", text).strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]+", text.lower())


def _hash_embed(text: str, dimension: int) -> list[float]:
    vector = [0.0] * dimension
    for token in _tokenize(text):
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % dimension
        weight = 1.0 + (int(digest[8:10], 16) / 255.0)
        vector[index] += weight
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", _normalize_text(text)).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


_STOP_WORDS = {
    "我们",
    "他们",
    "以及",
    "对于",
    "目前",
    "其中",
    "进行",
    "表示",
    "文章",
    "认为",
    "指出",
    "可以",
    "如果",
    "因为",
    "这个",
    "那个",
    "市场",
    "公司",
    "行业",
    "方面",
    "策略",
    "资产",
    "投资者",
    "配置",
    "收益",
    "影响",
    "风险偏好",
}


def _clean_list(value: Any, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized = [str(item).strip() for item in value if str(item).strip()]
    return normalize_tag_items(normalized, limit=limit)


def _extract_json_payload(text: str) -> dict[str, Any]:
    payload = text.strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, count=1, flags=re.IGNORECASE)
    payload = re.sub(r"\s*```$", "", payload, count=1)
    payload = re.sub(r"<think>.*?</think>", "", payload, flags=re.DOTALL | re.IGNORECASE).strip()
    start = payload.find("{")
    end = payload.rfind("}")
    if start >= 0 and end > start:
        payload = payload[start : end + 1]
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object")
    return data


def _heuristic_format_text(text: str) -> str:
    normalized = _normalize_text(text)
    blocks = [block.strip() for block in re.split(r"\n{2,}", normalized) if block.strip()]
    if not blocks:
        blocks = [line.strip() for line in normalized.splitlines() if line.strip()]

    paragraphs: list[str] = []
    buffer = ""
    for block in blocks:
        compact = re.sub(r"\s+", " ", block).strip()
        if not compact:
            continue
        if len(compact) < 36 and not re.search(r"[。！？；?!]$", compact):
            buffer = f"{buffer}{compact}" if buffer else compact
            continue
        if buffer:
            compact = f"{buffer}{compact}"
            buffer = ""
        paragraphs.append(compact)
    if buffer:
        paragraphs.append(buffer)
    return "\n\n".join(paragraphs)


def _split_sentences(text: str) -> list[str]:
    sentences = [segment.strip() for segment in re.split(r"(?<=[。！？；?!])\s*", _normalize_text(text)) if segment.strip()]
    if sentences:
        return sentences
    return [line.strip() for line in _normalize_text(text).splitlines() if line.strip()]


def _token_overlap_ratio(source: str, candidate: str) -> float:
    source_tokens = {token for token in _tokenize(source) if len(token) > 1}
    candidate_tokens = {token for token in _tokenize(candidate) if len(token) > 1 and token not in _STOP_WORDS}
    if not candidate_tokens:
        return 1.0
    overlap = candidate_tokens & source_tokens
    return len(overlap) / len(candidate_tokens)


def _is_grounded_summary(source: str, candidate: str) -> bool:
    if not candidate.strip():
        return False
    source_tokens = {token for token in _tokenize(source) if len(token) > 1}
    candidate_tokens = {token for token in _tokenize(candidate) if len(token) > 1 and token not in _STOP_WORDS}
    overlap_ratio = _token_overlap_ratio(source, candidate)
    novel_tokens = {token for token in candidate_tokens if token not in source_tokens}
    novel_ratio = len(novel_tokens) / len(candidate_tokens) if candidate_tokens else 0.0
    return overlap_ratio >= 0.7 and novel_ratio <= 0.3


def _heuristic_summary(text: str, limit: int = 180) -> str:
    formatted = _heuristic_format_text(text)
    sentences = _split_sentences(formatted)
    if not sentences:
        return _truncate(formatted, limit)

    scored: list[tuple[float, int, str]] = []
    finance_keywords = (
        "政策",
        "利率",
        "汇率",
        "流动性",
        "通胀",
        "增长",
        "财报",
        "业绩",
        "估值",
        "风险",
        "需求",
        "供给",
        "利润",
        "营收",
        "美元",
        "原油",
        "降息",
        "降准",
    )
    for index, sentence in enumerate(sentences):
        score = 0.0
        score += max(0, 6 - index) * 0.2
        score += min(len(sentence), 80) / 120.0
        score += sum(1.0 for keyword in finance_keywords if keyword in sentence)
        if re.search(r"\d", sentence):
            score += 0.4
        scored.append((score, index, sentence))

    scored.sort(key=lambda item: (-item[0], item[1]))
    chosen = sorted(scored[:3], key=lambda item: item[1])
    summary = "".join(sentence for _score, _index, sentence in chosen)
    return _truncate(summary, limit)


def _markdown_from_sections(title: str, overview: str, sections: list[dict[str, Any]], follow_ups: list[str]) -> str:
    lines = [f"# {title}", ""]
    if overview:
        lines.extend(["## 概览", overview, ""])
    for section in sections:
        lines.append(f"## {section.get('title', '未命名分区')}")
        summary = str(section.get("summary") or "").strip()
        if summary:
            lines.append(summary)
        for bullet in section.get("bullets") or []:
            bullet_text = str(bullet).strip()
            if bullet_text:
                lines.append(f"- {bullet_text}")
        lines.append("")
    if follow_ups:
        lines.append("## 后续关注")
        for item in follow_ups:
            item_text = str(item).strip()
            if item_text:
                lines.append(f"- {item_text}")
        lines.append("")
    return "\n".join(lines).strip()


class RuleBasedProvider:
    name = "rule"

    def __init__(self, settings: Settings):
        self.settings = settings

    def summarize(self, text: str) -> str:
        return _heuristic_summary(text, 180)

    def extract_features(self, text: str) -> dict[str, Any]:
        formatted_text = _heuristic_format_text(text)
        return {
            "summary": self.summarize(formatted_text),
            "formatted_text": formatted_text,
            "topic_tags": suggest_topic_tags(formatted_text, limit=8),
            "entity_tags": extract_entity_tags(formatted_text, limit=8),
            "content_type": suggest_content_type(formatted_text),
            "core_claims": suggest_core_claims(formatted_text, limit=4),
            "key_variables": suggest_key_variables(formatted_text, limit=5),
            "catalysts": suggest_catalysts(formatted_text, limit=3),
            "risks": suggest_risks(formatted_text, limit=3),
            "style_tags": suggest_style_tags(formatted_text, limit=4),
            "taxonomy_version": TAXONOMY_VERSION,
            "analysis_mode": "rule_fallback",
        }

    def generate_daily_report(self, context: dict[str, Any]) -> dict[str, Any]:
        date = context.get("date", "")
        articles = context.get("articles", [])
        groups = context.get("source_groups", [])
        top_tags = context.get("top_topic_tags", [])
        top_entities = context.get("top_entities", [])

        overview_parts: list[str] = []
        if articles:
            overview_parts.append(f"当日共纳入 {len(articles)} 篇文章，覆盖 {len(groups)} 个来源分组。")
        if top_tags:
            overview_parts.append("高频主题包括 " + "、".join(f"{tag}({count})" for tag, count in top_tags[:5]) + "。")
        if top_entities:
            overview_parts.append("高频实体包括 " + "、".join(f"{name}({count})" for name, count in top_entities[:5]) + "。")
        overview = " ".join(overview_parts) if overview_parts else "当日暂无可分析文章。"

        sections: list[dict[str, Any]] = []
        for group in groups[:5]:
            bullets = []
            for article in group.get("articles", [])[:3]:
                summary = article.get("summary") or article.get("title") or ""
                bullets.append(f"{article.get('source_name', '')}：{article.get('title', '')}。{_truncate(summary, 90)}")
            sections.append(
                {
                    "title": group.get("group") or "未分组",
                    "summary": f"{group.get('article_count', 0)} 篇文章，来自 {group.get('source_count', 0)} 个公众号。",
                    "bullets": bullets,
                    "article_ids": [article.get("id") for article in group.get("articles", [])[:5] if article.get("id")],
                }
            )

        follow_ups = [f"继续跟踪 {tag} 的新增文章和后续变化。" for tag, _count in top_tags[:5]]
        title = f"{date} 公众号日报" if date else "公众号日报"
        return {
            "title": title,
            "overview": overview,
            "sections": sections,
            "follow_ups": follow_ups,
            "report_markdown": _markdown_from_sections(title, overview, sections, follow_ups),
        }

    def embed_text(self, text: str) -> list[float]:
        return _hash_embed(text, self.settings.embed_dimension)


@dataclass
class OpenAICompatibleProvider:
    settings: Settings
    name: str = "openai_compatible"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        if self.settings.openai_organization:
            headers["OpenAI-Organization"] = self.settings.openai_organization
        return headers

    def _request_payload(self, system: str, user: str) -> dict[str, Any]:
        return {
            "model": self.settings.openai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.settings.openai_temperature,
        }

    def _extract_message_content(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices") or []
        if not choices:
            raise ValueError("LLM response missing choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_value = str(item.get("text") or "").strip()
                    if text_value:
                        parts.append(text_value)
            if parts:
                return "\n".join(parts).strip()
        raise ValueError("LLM response missing message content")

    def _client_kwargs(self) -> dict[str, Any]:
        return {
            "timeout": self.settings.openai_timeout_seconds,
            "follow_redirects": True,
            "verify": self.settings.openai_verify_ssl,
            "headers": self._headers(),
        }

    def _chat_completion(self, *, system: str, user: str) -> str:
        url = urljoin(self.settings.openai_base_url.rstrip("/") + "/", "chat/completions")
        payload = self._request_payload(system, user)
        last_error: Exception | None = None
        for attempt in range(1, max(self.settings.openai_max_retries, 1) + 1):
            try:
                if attempt > 1:
                    logger.info("Retrying LLM request to %s (attempt %s)", self.settings.openai_base_url, attempt)
                with httpx.Client(**self._client_kwargs()) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    return self._extract_message_content(response.json())
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPError) as exc:
                last_error = exc
                if attempt >= self.settings.openai_max_retries:
                    break

        if last_error:
            raise last_error
        raise RuntimeError("LLM request failed without a concrete error")

    def summarize(self, text: str) -> str:
        if not self.settings.openai_api_key:
            return RuleBasedProvider(self.settings).summarize(text)
        try:
            return self._chat_completion(
                system="你是一名严谨的中文财经编辑。请输出一段 100 到 140 字的摘要，只保留关键事实、判断和影响，不要照抄原文开头，不要输出标题。",
                user=f"请总结下面这篇文章的核心事实、判断和影响，避免照抄原句：\n\n{text}",
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("LLM summarize failed, fallback to rule provider: %s", exc)
            return RuleBasedProvider(self.settings).summarize(text)

    def extract_features(self, text: str) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            return RuleBasedProvider(self.settings).extract_features(text)

        system = (
            "你是一名严谨的中文财经内容分析助手。"
            "你必须只返回 JSON 对象，不要输出解释、前言、代码块或额外文本。"
        )
        user = (
            f"{taxonomy_prompt_block()}\n"
            "请基于文章内容返回 JSON，字段如下：\n"
            "{\n"
            '  "summary": "100到140字的中文摘要，禁止照抄文章前两句",\n'
            '  "formatted_text": "重新排版后的正文，保留原意，不新增事实",\n'
            '  "topic_tags": ["从给定标签体系中选择"],\n'
            '  "entity_tags": ["公司、机构、人物、产品等实体"],\n'
            '  "content_type": "深度研究|快讯|复盘|访谈|数据解读|公告解读|观点|新闻",\n'
            '  "core_claims": ["2到4条核心判断"],\n'
            '  "key_variables": ["影响结论的关键变量"],\n'
            '  "catalysts": ["可能的催化因素"],\n'
            '  "risks": ["主要风险"],\n'
            '  "style_tags": ["从给定样式标签中选择"]\n'
            "}\n"
            "要求：formatted_text 只做排版、换段和轻量去噪；"
            "summary 必须概括全文而不是截取开头；"
            "topic_tags 和 style_tags 只能从给定体系中选择；"
            "如果文章是行业新闻，不要误标成宏观政策。\n\n"
            f"文章内容：\n{text}"
        )

        try:
            raw = self._chat_completion(system=system, user=user)
            data = _extract_json_payload(raw)
            formatted_text = str(data.get("formatted_text") or "").strip() or _heuristic_format_text(text)
            heuristic_topic_tags = suggest_topic_tags(formatted_text, limit=8)
            topic_tags = normalize_tag_items(_clean_list(data.get("topic_tags")), allowed=TOPIC_TAG_SET, limit=8)
            guarded = False
            if heuristic_topic_tags and not set(topic_tags).intersection(heuristic_topic_tags):
                topic_tags = heuristic_topic_tags
                guarded = True
            style_tags = normalize_tag_items(_clean_list(data.get("style_tags")), allowed=STYLE_TAG_SET, limit=4)
            content_type = str(data.get("content_type") or "").strip()
            if content_type not in CONTENT_TYPE_SET:
                content_type = suggest_content_type(formatted_text)
                guarded = True
            summary = _truncate(str(data.get("summary") or "").strip(), 180)
            if not _is_grounded_summary(formatted_text, summary):
                summary = RuleBasedProvider(self.settings).summarize(formatted_text)
                guarded = True
            return {
                "summary": summary or self.summarize(formatted_text),
                "formatted_text": formatted_text,
                "topic_tags": topic_tags or heuristic_topic_tags,
                "entity_tags": normalize_tag_items(_clean_list(data.get("entity_tags")), limit=8)
                or extract_entity_tags(formatted_text, limit=8),
                "content_type": content_type,
                "core_claims": normalize_tag_items(_clean_list(data.get("core_claims")), limit=4)
                or suggest_core_claims(formatted_text, limit=4),
                "key_variables": normalize_tag_items(_clean_list(data.get("key_variables")), limit=5)
                or suggest_key_variables(formatted_text, limit=5),
                "catalysts": normalize_tag_items(_clean_list(data.get("catalysts")), limit=5)
                or suggest_catalysts(formatted_text, limit=3),
                "risks": normalize_tag_items(_clean_list(data.get("risks")), limit=5)
                or suggest_risks(formatted_text, limit=3),
                "style_tags": style_tags or suggest_style_tags(formatted_text, limit=4),
                "taxonomy_version": TAXONOMY_VERSION,
                "analysis_mode": "llm_guarded" if guarded else "llm",
            }
        except Exception as exc:  # pragma: no cover
            logger.warning("LLM feature extraction failed, fallback to rule provider: %s", exc)
            return RuleBasedProvider(self.settings).extract_features(text)

    def generate_daily_report(self, context: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            return RuleBasedProvider(self.settings).generate_daily_report(context)

        system = (
            "你是一名严谨的中文财经日报编辑。"
            "你必须只返回 JSON 对象，不要输出代码块、解释或额外说明。"
        )
        user = (
            "请根据给定的公众号文章集合生成一份日报。"
            "日报要综合利用来源分组、来源标签、文章摘要和文章主题标签。\n"
            "输出 JSON：\n"
            "{\n"
            '  "title": "日报标题",\n'
            '  "overview": "整体概览",\n'
            '  "sections": [{"title": "...", "summary": "...", "bullets": ["..."], "article_ids": ["..."]}],\n'
            '  "follow_ups": ["..."]\n'
            "}\n"
            "要求：sections 2 到 6 个；每个 section 2 到 5 条 bullet；article_ids 必须来自输入的 article.id。\n"
            f"输入数据：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        )

        try:
            raw = self._chat_completion(system=system, user=user)
            data = _extract_json_payload(raw)
            sections = []
            for section in data.get("sections", []) or []:
                if not isinstance(section, dict):
                    continue
                sections.append(
                    {
                        "title": str(section.get("title") or "未命名分区").strip(),
                        "summary": str(section.get("summary") or "").strip() or None,
                        "bullets": _clean_list(section.get("bullets"), limit=5),
                        "article_ids": _clean_list(section.get("article_ids"), limit=10),
                    }
                )
            title = str(data.get("title") or f"{context.get('date', '')} 公众号日报").strip()
            overview = str(data.get("overview") or "").strip()
            follow_ups = _clean_list(data.get("follow_ups"), limit=5)
            return {
                "title": title,
                "overview": overview,
                "sections": sections,
                "follow_ups": follow_ups,
                "report_markdown": _markdown_from_sections(title, overview, sections, follow_ups),
            }
        except Exception as exc:  # pragma: no cover
            logger.warning("LLM daily report failed, fallback to rule provider: %s", exc)
            return RuleBasedProvider(self.settings).generate_daily_report(context)

    def embed_text(self, text: str) -> list[float]:
        return RuleBasedProvider(self.settings).embed_text(text)


def build_provider(settings: Settings):
    if settings.llm_provider.lower() in {"openai", "openai_compatible"} and settings.openai_api_key:
        return OpenAICompatibleProvider(settings)
    return RuleBasedProvider(settings)
