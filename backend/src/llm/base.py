from __future__ import annotations

from collections.abc import Protocol


class LLMProvider(Protocol):
    name: str

    def summarize(self, text: str) -> str: ...

    def extract_features(self, text: str) -> dict: ...

    def classify_source(self, source_name: str, article_titles: list[str]) -> dict: ...

    def embed_text(self, text: str) -> list[float]: ...
