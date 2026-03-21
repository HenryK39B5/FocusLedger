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


def _clean_list(value: Any, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized = [str(item).strip() for item in value if str(item).strip()]
    return normalize_tag_items(normalized, limit=limit)


def _extract_json_payload(text: str) -> dict[str, Any]:
    payload = text.strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, count=1, flags=re.IGNORECASE)
        payload = re.sub(r"\s*```$", "", payload, count=1)
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
        if len(compact) < 36 and not re.search(r"[。！？；：.!?]$", compact):
            buffer = f"{buffer}{compact}" if buffer else compact
            continue
        if buffer:
            compact = f"{buffer}{compact}"
            buffer = ""
        paragraphs.append(compact)
    if buffer:
        paragraphs.append(buffer)
    return "\n\n".join(paragraphs)


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
        return _truncate(text, 180)

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
        return {
          "Authorization": f"Bearer {self.settings.openai_api_key}",
          "Content-Type": "application/json",
        }

    def _chat_completion(self, *, system: str, user: str) -> str:
        response = httpx.post(
            urljoin(self.settings.openai_base_url.rstrip("/") + "/", "chat/completions"),
            headers=self._headers(),
            json={
                "model": self.settings.openai_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=45,
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"].strip()

    def summarize(self, text: str) -> str:
        if not self.settings.openai_api_key:
            return RuleBasedProvider(self.settings).summarize(text)
        try:
            return self._chat_completion(
                system="你是一名严谨的中文财经编辑。只输出摘要正文，不要输出额外解释。",
                user=f"请用中文在 120 字以内总结下面这篇文章：\n{text}",
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("LLM summarize failed, fallback to rule provider: %s", exc)
            return RuleBasedProvider(self.settings).summarize(text)

    def extract_features(self, text: str) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            return RuleBasedProvider(self.settings).extract_features(text)

        system = "你是一名严谨的中文财经内容分析助手。必须只返回 JSON，不要附带解释。"
        user = (
            f"{taxonomy_prompt_block()}\n"
            "请基于文章内容输出 JSON，字段如下：\n"
            "{\n"
            '  "summary": "120字以内摘要",\n'
            '  "formatted_text": "重新整理段落后的正文，保持原意，不添加新信息",\n'
            '  "topic_tags": ["..."],\n'
            '  "entity_tags": ["..."],\n'
            '  "content_type": "深度研究|快讯|复盘|访谈|数据解读|公告解读|观点|新闻",\n'
            '  "core_claims": ["..."],\n'
            '  "key_variables": ["..."],\n'
            '  "catalysts": ["..."],\n'
            '  "risks": ["..."],\n'
            '  "style_tags": ["..."]\n'
            "}\n"
            "要求：formatted_text 只做排版、换段和轻度去噪，不要删除重要信息；"
            "topic_tags 和 style_tags 只能从给定体系里选；entity_tags 不超过 8 个。\n"
            f"文章内容：\n{text}"
        )

        try:
            raw = self._chat_completion(system=system, user=user)
            data = _extract_json_payload(raw)
            formatted_text = str(data.get("formatted_text") or "").strip() or _heuristic_format_text(text)
            topic_tags = normalize_tag_items(_clean_list(data.get("topic_tags")), allowed=TOPIC_TAG_SET, limit=8)
            style_tags = normalize_tag_items(_clean_list(data.get("style_tags")), allowed=STYLE_TAG_SET, limit=4)
            content_type = str(data.get("content_type") or "").strip()
            if content_type not in CONTENT_TYPE_SET:
                content_type = suggest_content_type(formatted_text)
            return {
                "summary": _truncate(str(data.get("summary") or self.summarize(formatted_text)), 180),
                "formatted_text": formatted_text,
                "topic_tags": topic_tags or suggest_topic_tags(formatted_text, limit=8),
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
            }
        except Exception as exc:  # pragma: no cover
            logger.warning("LLM feature extraction failed, fallback to rule provider: %s", exc)
            return RuleBasedProvider(self.settings).extract_features(text)

    def generate_daily_report(self, context: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            return RuleBasedProvider(self.settings).generate_daily_report(context)

        system = "你是一名严谨的中文财经日报编辑。必须只返回 JSON，不要输出代码块或多余说明。"
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
            "要求：sections 2 到 6 个；每个 section 2 到 5 个 bullet；article_ids 必须来自输入的 article.id。\n"
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
