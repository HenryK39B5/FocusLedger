from __future__ import annotations

from collections.abc import Protocol


class LLMProvider(Protocol):
    name: str

    def summarize(self, text: str) -> str: ...

    def extract_features(self, text: str) -> dict: ...

    def generate_daily_report(self, context: dict) -> dict: ...

    def embed_text(self, text: str) -> list[float]: ...
