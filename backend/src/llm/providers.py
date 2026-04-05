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
from src.llm.taxonomy_files import load_article_tag_taxonomy, load_source_group_taxonomy, load_source_tag_taxonomy

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


def _normalize_summary_text(text: str) -> str:
    return re.sub(r"\s+", " ", _normalize_text(text)).strip()


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

    def classify_source(self, source_name: str, article_titles: list[str]) -> dict[str, Any]:
        raise RuntimeError("LLM provider unavailable; source classification requires a real LLM API")

    def answer_notebook_question(
        self,
        *,
        notebook_name: str,
        notebook_description: str | None,
        history: list[dict[str, Any]],
        articles: list[dict[str, Any]],
        question: str,
    ) -> dict[str, Any]:
        raise RuntimeError("LLM provider unavailable; notebook chat requires a real LLM API")

    def generate_podcast_script(
        self,
        *,
        notebook_name: str,
        notebook_description: str | None,
        podcast_format: str,
        target_minutes: int,
        focus_prompt: str | None,
        articles: list[dict[str, Any]],
    ) -> dict[str, Any]:
        raise RuntimeError("LLM provider unavailable; podcast script generation requires a real LLM API")


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
            "trust_env": False,
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
            raise RuntimeError("LLM API key is not configured")
        return self._chat_completion(
            system="你是一名严谨的中文研究助理。请只输出一段中文摘要，不要标题，不要项目符号，不要解释。",
            user=(
                "请基于全文写一段 90 到 140 字的中文摘要。\n"
                "要求：\n"
                "1. 必须基于全文，不要摘抄开头两句。\n"
                "2. 要覆盖核心事件、主要判断和潜在影响。\n"
                "3. 不要添加原文中没有的新事实。\n\n"
                f"文章全文：\n{text}"
            ),
        )

    def extract_features(self, text: str) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise RuntimeError("LLM API key is not configured")

        allowed_tags = load_article_tag_taxonomy()
        system = (
            "你是一名严谨的中文文章整理助手。"
            "你的任务只有两个：写摘要、打标签。"
            "你必须只返回 JSON 对象，不要解释，不要代码块，不要额外文本。"
        )
        user = (
            "请基于全文返回 JSON：\n"
            "{\n"
            '  "summary": "90到140字的一段话中文摘要",\n'
            '  "topic_tags": ["2到6个标签"]\n'
            "}\n\n"
            "摘要要求：\n"
            "1. 必须基于全文，不要摘抄开头两句。\n"
            "2. 要覆盖核心事件、主要判断和潜在影响。\n"
            "3. 不要添加原文没有的新事实。\n"
            "4. 不要使用项目符号，不要输出标题。\n\n"
            "标签要求：\n"
            "1. 只能从给定标签列表中选择。\n"
            "2. 输出 2 到 6 个最相关标签。\n"
            "3. 如果文章与某类标签关联不强，就不要硬选。\n"
            "4. 多级标签可以直接原样输出。\n\n"
            f"可选标签列表：{json.dumps(allowed_tags, ensure_ascii=False)}\n\n"
            f"文章全文：\n{text}"
        )

        raw = self._chat_completion(system=system, user=user)
        data = _extract_json_payload(raw)
        summary = _normalize_summary_text(str(data.get("summary") or ""))
        topic_tags = normalize_tag_items(_clean_list(data.get("topic_tags")), allowed=set(allowed_tags), limit=8)
        if not summary:
            raise ValueError("LLM summary is empty")
        return {
            "summary": summary,
            "formatted_text": _heuristic_format_text(text),
            "topic_tags": topic_tags,
            "entity_tags": [],
            "content_type": None,
            "core_claims": [],
            "key_variables": [],
            "catalysts": [],
            "risks": [],
            "style_tags": [],
            "taxonomy_version": TAXONOMY_VERSION,
            "analysis_mode": "llm",
        }

    def classify_source(self, source_name: str, article_titles: list[str]) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise RuntimeError("LLM API key is not configured")

        allowed_groups = load_source_group_taxonomy()
        allowed_tags = load_source_tag_taxonomy()
        preview_titles = [title.strip() for title in article_titles if title.strip()][:20]
        system = (
            "你是一名严谨的中文内容研究助理。"
            "你的任务是根据公众号名称和其历史文章标题，为公众号选择一个分组，并打上 2 到 5 个标签。"
            "你必须只返回 JSON 对象，不要解释，不要代码块，不要额外文本。"
        )
        user = (
            "请根据下面的信息为公众号做分类。\n"
            "输出 JSON：\n"
            "{\n"
            '  "source_group": "一个分组路径",\n'
            '  "tags": ["2到5个标签"],\n'
            '  "reason": "一句简短说明"\n'
            "}\n\n"
            "要求：\n"
            "1. source_group 只能从给定分组列表中选择一个。\n"
            "2. tags 只能从给定标签列表中选择，输出 2 到 5 个。\n"
            "3. 优先根据公众号名称和历史文章标题判断长期定位，而不是单篇偶发主题。\n"
            "4. 不要发明分组或标签。\n\n"
            f"公众号名称：{source_name}\n"
            f"历史文章标题：{json.dumps(preview_titles, ensure_ascii=False)}\n"
            f"可选分组：{json.dumps(allowed_groups, ensure_ascii=False)}\n"
            f"可选标签：{json.dumps(allowed_tags, ensure_ascii=False)}"
        )
        raw = self._chat_completion(system=system, user=user)
        data = _extract_json_payload(raw)
        source_group = str(data.get("source_group") or "").strip()
        tags = normalize_tag_items(_clean_list(data.get("tags")), allowed=set(allowed_tags), limit=5)
        if source_group not in allowed_groups:
            raise ValueError("LLM returned an invalid source group")
        if not tags:
            raise ValueError("LLM returned empty source tags")
        return {
            "source_group": source_group,
            "tags": tags,
            "reason": str(data.get("reason") or "").strip() or None,
        }

    def answer_notebook_question(
        self,
        *,
        notebook_name: str,
        notebook_description: str | None,
        history: list[dict[str, Any]],
        articles: list[dict[str, Any]],
        question: str,
    ) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise RuntimeError("LLM API key is not configured")

        system = (
            "你正在 FocusLedger 中工作。"
            "FocusLedger 是一个面向中文微信公众号文章的本地研究与内容整理工具，用户会先把公众号文章同步到本地，再把相关文章放入 Notebook 作为专题来源。"
            "Notebook 的定位是一个围绕特定研究主题组织来源文章、持续提问、整理观点和生成后续输出的工作区。"
            "你在这里不是做泛化闲聊，而是作为严谨的中文研究助理，围绕当前 Notebook 中的来源文章帮助用户理解、比较、归纳和判断。"
            "你必须优先依据提供的 Notebook 说明、历史对话和来源文章作答，不要编造来源中没有的信息。"
            "如果材料不足以支撑明确结论，要直接说明信息不足，不要装作已经确认。"
            "你必须只返回 JSON 对象，不要解释，不要代码块，不要额外文本。"
        )
        user = (
            "请基于给定 Notebook 上下文回答当前问题。\n"
            "输出 JSON：\n"
            "{\n"
            '  "answer": "一段到三段中文回答",\n'
            '  "citations": ["article_id1", "article_id2"]\n'
            "}\n\n"
            "要求：\n"
            "1. 回答应直接回应问题，优先帮助用户完成研究、梳理和比较，而不是泛泛而谈。\n"
            "2. 如果来源文章之间存在明显分歧，要指出主要分歧点，不要强行合并成一个结论。\n"
            "3. 如果 Notebook 里的材料不足以支持明确结论，要明确说信息不足。\n"
            "4. citations 只允许从给定 article_id 中选择 0 到 4 个最相关的文章。\n"
            "5. 不要输出 markdown 标题，不要把 citations 写进 answer 正文。\n"
            "6. 回答可以适度组织结构，但不要写成模板化空话。\n\n"
            f"Notebook 名称：{notebook_name}\n"
            f"Notebook 说明：{notebook_description or '无'}\n"
            f"最近对话：{json.dumps(history, ensure_ascii=False)}\n"
            f"来源文章：{json.dumps(articles, ensure_ascii=False)}\n"
            f"当前问题：{question.strip()}"
        )
        raw = self._chat_completion(system=system, user=user)
        data = _extract_json_payload(raw)
        answer = _normalize_text(str(data.get("answer") or ""))
        citations = _clean_list(data.get("citations"), limit=4)
        if not answer:
            raise ValueError("LLM notebook answer is empty")
        allowed_ids = {str(item.get("id")) for item in articles if item.get("id")}
        citations = [item for item in citations if item in allowed_ids]
        return {
            "answer": answer,
            "citations": citations,
        }

    def generate_podcast_script(
        self,
        *,
        notebook_name: str,
        notebook_description: str | None,
        podcast_format: str,
        target_minutes: int,
        focus_prompt: str | None,
        articles: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise RuntimeError("LLM API key is not configured")

        format_instructions = {
            "brief": "Brief：单人超短综述，重点是快速交代这个 Notebook 的核心信息，不展开过多细节。",
            "explainer": "Explainer：单人专题讲解，重点是把主题讲清楚，结构完整，有背景、有主线、有结论。",
            "commentary": "Commentary：单人研究评论，重点是提炼值得关注的判断、分歧和后续观察点，而不只是复述。",
        }
        active_instruction = format_instructions.get(
            podcast_format,
            format_instructions["explainer"],
        )

        system = (
            "你正在 FocusLedger 中工作。"
            "FocusLedger 是一个面向中文微信公众号文章的本地研究与内容整理工具，用户会把相关文章放入 Notebook，围绕一个主题持续研究。"
            "现在你的任务不是生成音频，而是先为后续音频渲染写出一份适合朗读和收听的中文播客脚本。"
            "当前阶段脚本全部是单人讲述，不要写成双人对谈。"
            "你必须优先依据给定的 Notebook 说明和来源文章组织脚本，不要编造来源中没有的信息。"
            "你必须只返回 JSON 对象，不要解释，不要代码块，不要额外文本。"
        )
        user = (
            "请为当前 Notebook 生成播客脚本。\n"
            "脚本格式说明：\n"
            f"{active_instruction}\n\n"
            "输出 JSON：\n"
            "{\n"
            '  "title": "脚本标题",\n'
            '  "one_line_summary": "一句话概括",\n'
            '  "speakers": [{"id": "host", "display_name": "主持人", "voice_hint": "single_host"}],\n'
            '  "sections": [\n'
            '    {"id": "intro", "title": "段落标题", "objective": "这一段要完成什么", "turns": [{"speaker_id": "host", "text": "可朗读文本", "citations": ["article_id"]}]}\n'
            "  ],\n"
            '  "cited_article_ids": ["article_id1", "article_id2"]\n'
            "}\n\n"
            "要求：\n"
            "1. 只允许单个 speaker：host。\n"
            "2. sections 控制在 3 到 6 段。\n"
            "3. 每段 turns 当前只输出 1 个 turn，speaker_id 固定为 host。\n"
            "4. 文本必须适合听觉消费，避免书面腔过重，适合直接朗读。\n"
            "5. 不要空喊口号，不要模板化结尾，不要假装知道来源里没有的事实。\n"
            "6. cited_article_ids 与 turn.citations 只能从给定 article_id 中选择。\n"
            "7. 目标时长约为 "
            f"{target_minutes} 分钟，请控制整体信息密度和脚本长度。\n"
            "8. 如果来源之间存在明显分歧，要明确点出，不要强行合并。\n"
            "9. 如果用户给了 focus_prompt，要优先围绕那个重点组织脚本。\n\n"
            f"Notebook 名称：{notebook_name}\n"
            f"Notebook 说明：{notebook_description or '无'}\n"
            f"目标格式：{podcast_format}\n"
            f"用户重点要求：{focus_prompt or '无'}\n"
            f"来源文章：{json.dumps(articles, ensure_ascii=False)}"
        )
        raw = self._chat_completion(system=system, user=user)
        data = _extract_json_payload(raw)

        title = str(data.get("title") or "").strip()
        if not title:
            raise ValueError("podcast script title is empty")

        one_line_summary = str(data.get("one_line_summary") or "").strip() or None
        speakers = data.get("speakers") if isinstance(data.get("speakers"), list) else []
        if not speakers:
            speakers = [{"id": "host", "display_name": "主持人", "voice_hint": "single_host"}]

        allowed_ids = {str(item.get("id")) for item in articles if item.get("id")}
        sections_raw = data.get("sections") if isinstance(data.get("sections"), list) else []
        sections: list[dict[str, Any]] = []
        cited_ids: list[str] = []

        for index, section in enumerate(sections_raw):
            if not isinstance(section, dict):
                continue
            turns_raw = section.get("turns") if isinstance(section.get("turns"), list) else []
            turns: list[dict[str, Any]] = []
            for turn in turns_raw[:1]:
                if not isinstance(turn, dict):
                    continue
                text = _normalize_text(str(turn.get("text") or ""))
                citations = [item for item in _clean_list(turn.get("citations"), limit=4) if item in allowed_ids]
                if not text:
                    continue
                turns.append(
                    {
                        "speaker_id": "host",
                        "text": text,
                        "citations": citations,
                    }
                )
                for citation_id in citations:
                    if citation_id not in cited_ids:
                        cited_ids.append(citation_id)
            if not turns:
                continue
            sections.append(
                {
                    "id": str(section.get("id") or f"section_{index + 1}").strip() or f"section_{index + 1}",
                    "title": str(section.get("title") or f"第 {index + 1} 段").strip() or f"第 {index + 1} 段",
                    "objective": str(section.get("objective") or "").strip() or None,
                    "turns": turns,
                }
            )

        if not sections:
            raise ValueError("podcast script sections are empty")

        explicit_citations = [item for item in _clean_list(data.get("cited_article_ids"), limit=12) if item in allowed_ids]
        for citation_id in explicit_citations:
            if citation_id not in cited_ids:
                cited_ids.append(citation_id)

        return {
            "title": title,
            "format": podcast_format,
            "target_minutes": target_minutes,
            "one_line_summary": one_line_summary,
            "speakers": speakers,
            "sections": sections,
            "cited_article_ids": cited_ids,
        }

    def embed_text(self, text: str) -> list[float]:
        return RuleBasedProvider(self.settings).embed_text(text)

    def generate_daily_report(self, context: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            return RuleBasedProvider(self.settings).generate_daily_report(context)

        system = "你是一名严谨的中文财经日报编辑。必须只返回 JSON，不要输出代码块或额外说明。"
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


def build_provider(settings: Settings):
    if settings.llm_provider.lower() in {"openai", "openai_compatible"} and settings.openai_api_key:
        return OpenAICompatibleProvider(settings)
    return RuleBasedProvider(settings)
