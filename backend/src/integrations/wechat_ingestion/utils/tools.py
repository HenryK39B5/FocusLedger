from __future__ import annotations

import random
import re
import time
from pathlib import Path


def sleep_short(min_seconds: float = 0.05, max_seconds: float = 0.35) -> None:
    time.sleep(round(random.uniform(min_seconds, max_seconds), 3))


def sleep_long(min_seconds: float = 0.2, max_seconds: float = 0.8) -> None:
    time.sleep(round(random.uniform(min_seconds, max_seconds), 3))


def sanitize_filename(value: str) -> str:
    value = re.sub(r'[\\/*?:"<>|]+', "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:120] or "untitled"


def ensure_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def article_storage_dir(root: str | Path, source_name: str, publish_time: str | None, title: str) -> Path:
    root_path = ensure_dir(root)
    source_dir = ensure_dir(root_path / sanitize_filename(source_name))
    slug = sanitize_filename(title)
    subdir = f"{publish_time.replace(':', '_') if publish_time else 'unknown'} {slug}"
    return ensure_dir(source_dir / subdir)
