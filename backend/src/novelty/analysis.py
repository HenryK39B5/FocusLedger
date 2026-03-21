from __future__ import annotations


def _overlap(left: list[str], right: list[str]) -> list[str]:
    left_set = {item.strip().lower() for item in left if item}
    right_set = {item.strip().lower() for item in right if item}
    return sorted(left_set & right_set)


def analyze_novelty(article, history: list) -> dict:
    compared_ids = [item.id for item in history[:5]]
    repeated = []
    for item in history[:5]:
        repeated.extend(_overlap(article.topic_tags, item.topic_tags))
        repeated.extend(_overlap(article.entity_tags, item.entity_tags))
    repeated = sorted(set(repeated))
    current_set = set(article.topic_tags + article.entity_tags + article.core_claims)
    history_set = set()
    for item in history[:5]:
        history_set.update(item.topic_tags)
        history_set.update(item.entity_tags)
        history_set.update(item.core_claims)
    incremental = sorted({token for token in current_set - history_set if token})
    novelty_score = min(1.0, max(0.1, len(incremental) / max(len(current_set) or 1, 1)))
    breakdown = {
        "new_facts": len(incremental),
        "repeated_points": len(repeated),
        "historical_overlap": len(repeated) / max(len(current_set) or 1, 1),
    }
    explanation = "新增信息集中在" + "、".join(incremental[:5]) if incremental else "与历史内容高度重合"
    return {
        "compared_article_ids": compared_ids,
        "repeated_points": repeated,
        "incremental_points": incremental,
        "novelty_type_breakdown": breakdown,
        "novelty_score": round(novelty_score, 4),
        "explanation": explanation,
    }

