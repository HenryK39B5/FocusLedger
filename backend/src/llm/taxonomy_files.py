from __future__ import annotations

from functools import lru_cache
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TAXONOMY_DIR = REPO_ROOT / "docs" / "taxonomies"


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _extract_section_bullets(path: Path, heading: str) -> list[str]:
    items: list[str] = []
    in_section = False
    for line in _read_lines(path):
        stripped = line.strip()
        if stripped == f"## {heading}":
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section or not stripped.startswith("- "):
            continue
        value = stripped[2:].strip()
        if value and value not in items:
            items.append(value)
    return items


@lru_cache(maxsize=1)
def load_source_group_taxonomy() -> list[str]:
    return _extract_section_bullets(TAXONOMY_DIR / "source-group-taxonomy.md", "分组候选")


@lru_cache(maxsize=1)
def load_source_tag_taxonomy() -> list[str]:
    return _extract_section_bullets(TAXONOMY_DIR / "source-tag-taxonomy.md", "标签候选")


@lru_cache(maxsize=1)
def load_article_tag_taxonomy() -> list[str]:
    return _extract_section_bullets(TAXONOMY_DIR / "article-tag-taxonomy.md", "主题标签")


@lru_cache(maxsize=1)
def load_article_content_type_taxonomy() -> list[str]:
    return _extract_section_bullets(TAXONOMY_DIR / "article-tag-taxonomy.md", "内容类型")
