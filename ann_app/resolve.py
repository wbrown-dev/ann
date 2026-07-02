from __future__ import annotations

import json
import re

import requests

from ann_app.config import (
    REQUEST_TIMEOUT_SECONDS,
    RESOLVE_GOOGLE_NEWS_URLS,
    USER_AGENT,
)
from ann_app.fetch import Candidate

_BATCHEXECUTE_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"

_ID = re.compile(r'data-n-a-id="([^"]+)"')
_SG = re.compile(r'data-n-a-sg="([^"]+)"')
_TS = re.compile(r'data-n-a-ts="([^"]+)"')


def _is_google_news_url(link: str) -> bool:
    return "news.google.com" in link


def _extract_params(html: str) -> tuple[str, int, str] | None:
    article_id = _ID.search(html)
    signature = _SG.search(html)
    timestamp = _TS.search(html)
    if not (article_id and signature and timestamp):
        return None
    try:
        ts = int(timestamp.group(1))
    except ValueError:
        return None
    return article_id.group(1), ts, signature.group(1)


def _build_payload(article_id: str, timestamp: int, signature: str) -> str:
    inner = [
        "garturlreq",
        [
            ["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
            "X",
            "X",
            1,
            [1, 1, 1],
            1,
            1,
            None,
            0,
            0,
            None,
            0,
        ],
        article_id,
        timestamp,
        signature,
    ]
    return json.dumps([[["Fbv4je", json.dumps(inner)]]])


def _parse_batchexecute(text: str) -> str | None:
    _prefix, _, rest = text.partition("\n")
    try:
        rows = json.loads(rest)
    except (ValueError, TypeError):
        return None
    for row in rows:
        if len(row) > 2 and row[1] == "Fbv4je" and row[2]:
            try:
                payload = json.loads(row[2])
            except (ValueError, TypeError):
                return None
            if len(payload) > 1 and isinstance(payload[1], str):
                return payload[1]
    return None


def _resolve(link: str, session: requests.Session) -> str | None:
    try:
        page = session.get(link, timeout=REQUEST_TIMEOUT_SECONDS)
        page.raise_for_status()
        params = _extract_params(page.text)
        if params is None:
            return None
        resp = session.post(
            _BATCHEXECUTE_URL,
            data={"f.req": _build_payload(*params)},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return _parse_batchexecute(resp.text)
    except requests.RequestException:
        return None


def resolve_google_news_url(
    link: str,
    *,
    session: requests.Session,
    cache: dict[str, str] | None = None,
) -> str:
    if not _is_google_news_url(link):
        return link
    if cache is not None and link in cache:
        return cache[link]
    resolved = _resolve(link, session) or link
    if cache is not None:
        cache[link] = resolved
    return resolved


def resolve_selection(selections: dict[str, list[Candidate]]) -> None:
    if not RESOLVE_GOOGLE_NEWS_URLS:
        return
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    cache: dict[str, str] = {}
    for candidates in selections.values():
        for candidate in candidates:
            candidate.link = resolve_google_news_url(candidate.link, session=session, cache=cache)
