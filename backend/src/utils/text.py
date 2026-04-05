from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_SUSPECT_TOKENS = (
    "Ã",
    "Â",
    "ä¸",
    "æ",
    "ç",
    "é",
    "å",
    "ï¼",
    "銆",
    "锛",
    "鏈",
    "褰",
    "鍙",
    "璇",
    "鏉",
    "缁",
    "闃",
    "鐭",
    "宸",
    "澶",
    "鎴",
)


def _mojibake_score(value: str) -> int:
    return sum(value.count(token) for token in _SUSPECT_TOKENS)


def _repair_once(value: str) -> str:
    candidates = [value]
    transforms = (
        ("latin-1", "utf-8"),
        ("cp1252", "utf-8"),
        ("gbk", "utf-8"),
    )
    for source_encoding, target_encoding in transforms:
        try:
            candidate = value.encode(source_encoding).decode(target_encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        candidates.append(candidate)

    best = value
    best_score = _mojibake_score(value)
    for candidate in candidates[1:]:
        candidate_score = _mojibake_score(candidate)
        if candidate_score < best_score:
            best = candidate
            best_score = candidate_score
    return best


def repair_text(value: str) -> str:
    current = value
    for _ in range(2):
        repaired = _repair_once(current)
        if repaired == current:
            break
        current = repaired
    return current


def repair_data(value: Any) -> Any:
    if isinstance(value, str):
        return repair_text(value)
    if isinstance(value, list):
        return [repair_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(repair_data(item) for item in value)
    if isinstance(value, Mapping):
        return {key: repair_data(item) for key, item in value.items()}
    return value
