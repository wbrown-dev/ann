from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime

from ann_app.fetch import Candidate

CACHE_VERSION = 1
DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")


class CacheError(RuntimeError):
    pass


def _cache_path(target_date: date, cache_dir: str) -> str:
    return os.path.join(cache_dir, f"candidates-{target_date.isoformat()}.json")


def _candidate_to_dict(c: Candidate) -> dict:
    return {
        "outlet": c.outlet,
        "title": c.title,
        "link": c.link,
        "summary": c.summary,
        "published": c.published.isoformat() if c.published else None,
    }


def _candidate_from_dict(d: dict) -> Candidate:
    published = d.get("published")
    return Candidate(
        outlet=d["outlet"],
        title=d["title"],
        link=d["link"],
        summary=d.get("summary", ""),
        published=datetime.fromisoformat(published).astimezone(UTC) if published else None,
    )


def save_candidates(
    candidates: list[Candidate], target_date: date, cache_dir: str | None = None
) -> str:
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)
    payload = {
        "version": CACHE_VERSION,
        "date": target_date.isoformat(),
        "candidates": [_candidate_to_dict(c) for c in candidates],
    }
    path = _cache_path(target_date, cache_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def load_candidates(target_date: date, cache_dir: str | None = None) -> list[Candidate]:
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    path = _cache_path(target_date, cache_dir)
    if not os.path.exists(path):
        raise CacheError(f"no candidate cache for {target_date.isoformat()} at {path}")

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    version = payload.get("version")
    if version != CACHE_VERSION:
        raise CacheError(
            f"cache version mismatch in {path}: found {version}, expected {CACHE_VERSION}"
        )

    return [_candidate_from_dict(d) for d in payload.get("candidates", [])]
