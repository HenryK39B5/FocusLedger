from __future__ import annotations

from types import SimpleNamespace

from src.novelty.analysis import analyze_novelty
from src.ranking.scoring import score_article


def test_score_article_returns_explanations():
    article = SimpleNamespace(
        topic_tags=["宏观", "消费"],
        content_type="深度",
        style_tags=["结构化"],
        publish_time="2026-03-19T00:00:00+00:00",
    )
    profile = SimpleNamespace(
        preferred_topics=["宏观"],
        disliked_topics=[],
        preferred_content_types=["深度"],
        preferred_styles=["结构化"],
    )
    result = score_article(article, profile, novelty_score=0.8)
    assert result["ranking_score"] > 0
    assert "主题匹配" in result["explanation"]


def test_analyze_novelty_detects_overlap():
    article = SimpleNamespace(topic_tags=["AI", "消费"], entity_tags=["腾讯"], core_claims=["A"])
    history = [SimpleNamespace(id="1", topic_tags=["AI"], entity_tags=["阿里"], core_claims=["B"])]
    result = analyze_novelty(article, history)
    assert result["novelty_score"] > 0
    assert result["compared_article_ids"] == ["1"]

