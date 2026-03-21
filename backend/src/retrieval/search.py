from __future__ import annotations

from math import sqrt


def vector_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    length = min(len(left), len(right))
    dot = sum(left[i] * right[i] for i in range(length))
    left_norm = sqrt(sum(value * value for value in left[:length]))
    right_norm = sqrt(sum(value * value for value in right[:length]))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def find_similar_articles(target_embedding: list[float], candidates: list[tuple[object, list[float]]], limit: int = 5):
    scored = []
    for article, embedding in candidates:
        scored.append((article, vector_similarity(target_embedding, embedding)))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]

