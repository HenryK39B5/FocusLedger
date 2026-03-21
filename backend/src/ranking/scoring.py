from __future__ import annotations

from datetime import datetime, timezone


def _overlap_score(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    left = {item.strip().lower() for item in a if item}
    right = {item.strip().lower() for item in b if item}
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _freshness_score(publish_time: str | None) -> float:
    if not publish_time:
        return 0.5
    try:
        parsed = datetime.fromisoformat(publish_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_days = max((now - parsed.astimezone(timezone.utc)).days, 0)
        return max(0.0, 1.0 - min(age_days / 7.0, 1.0))
    except ValueError:
        return 0.5


def score_article(article, profile, novelty_score: float = 0.5) -> dict[str, float | str]:
    topic_match = _overlap_score(article.topic_tags, profile.preferred_topics)
    type_match = 1.0 if article.content_type in profile.preferred_content_types else 0.4
    style_match = _overlap_score(article.style_tags, profile.preferred_styles)
    freshness_score = _freshness_score(article.publish_time)
    penalty = _overlap_score(article.topic_tags, profile.disliked_topics)
    ranking_score = (
        topic_match * 0.35
        + type_match * 0.15
        + style_match * 0.15
        + freshness_score * 0.15
        + novelty_score * 0.2
        - penalty * 0.2
    )
    explanation = (
        f"主题匹配 {topic_match:.2f}，类型匹配 {type_match:.2f}，风格匹配 {style_match:.2f}，"
        f"新鲜度 {freshness_score:.2f}，增量 {novelty_score:.2f}。"
    )
    return {
        "topic_match_score": round(topic_match, 4),
        "type_match_score": round(type_match, 4),
        "style_match_score": round(style_match, 4),
        "novelty_score": round(novelty_score, 4),
        "freshness_score": round(freshness_score, 4),
        "ranking_score": round(max(ranking_score, 0.0), 4),
        "explanation": explanation,
    }

