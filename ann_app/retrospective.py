from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from ann_app.fetch import _normalize_title
from ann_app.parse import Headline, flatten_headlines, parse_digest

RETRO_MIN_DIGESTS = 2
RETRO_DEFAULT_DAYS = 7
RETRO_DEFAULT_TOP = 10

# Two headlines are treated as the same story when their salient-token sets
# overlap by at least this fraction of the smaller set and share at least this
# many tokens. Recall is favored over precision: missing a recurrence defeats
# the point of the retrospective, and a stray merge only mislabels one line.
_CLUSTER_CONTAINMENT = 0.4
_CLUSTER_MIN_OVERLAP = 2

_DIGEST_NAME = re.compile(r"headlines-(\d{4}-\d{2}-\d{2})\.md$")
_TOKEN = re.compile(r"[a-z0-9]+")

_STOPWORDS = {
    "this",
    "that",
    "with",
    "from",
    "into",
    "amid",
    "over",
    "after",
    "says",
    "said",
    "will",
    "could",
    "would",
    "than",
    "then",
    "your",
    "what",
    "when",
    "where",
    "here",
    "have",
    "been",
    "more",
    "most",
    "some",
    "their",
    "there",
}


@dataclass
class DigestFile:
    date: date
    path: str


@dataclass
class Story:
    title: str
    link: str | None
    outlets: list[str]
    dates: list[date]
    best_rank: int
    appearances: int


@dataclass
class RetroResult:
    digest_count: int
    latest_date: date | None
    span_start: date | None
    stories: list[Story] = field(default_factory=list)
    filename: str | None = None
    markdown: str = ""


def find_recent_digests(repo_root: str, days: int = RETRO_DEFAULT_DAYS) -> list[DigestFile]:
    files: list[DigestFile] = []
    for path in glob.glob(os.path.join(repo_root, "headlines-*.md")):
        match = _DIGEST_NAME.search(os.path.basename(path))
        if match:
            files.append(DigestFile(date=date.fromisoformat(match.group(1)), path=path))

    if not files:
        return []

    files.sort(key=lambda f: f.date)
    latest = files[-1].date
    cutoff = latest - timedelta(days=days - 1)
    return [f for f in files if f.date >= cutoff]


def _stem(token: str) -> str:
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _salient_tokens(title: str) -> set[str]:
    tokens = _TOKEN.findall(_normalize_title(title))
    return {_stem(t) for t in tokens if len(t) >= 4 and t not in _STOPWORDS}


def _matches(tokens: set[str], cluster_tokens: set[str]) -> bool:
    if not tokens or not cluster_tokens:
        return False
    overlap = len(tokens & cluster_tokens)
    if overlap < _CLUSTER_MIN_OVERLAP:
        return False
    smaller = min(len(tokens), len(cluster_tokens))
    return overlap / smaller >= _CLUSTER_CONTAINMENT


def cluster_stories(dated_headlines: list[tuple[date, list[Headline]]]) -> list[Story]:
    clusters: list[dict] = []
    for digest_date, headlines in dated_headlines:
        for headline in headlines:
            tokens = _salient_tokens(headline.title)
            placed = False
            for cluster in clusters:
                if _matches(tokens, cluster["tokens"]):
                    cluster["tokens"] |= tokens
                    cluster["members"].append((digest_date, headline))
                    placed = True
                    break
            if not placed:
                clusters.append({"tokens": set(tokens), "members": [(digest_date, headline)]})

    return [_to_story(cluster["members"]) for cluster in clusters]


def _to_story(members: list[tuple[date, Headline]]) -> Story:
    representative = min(
        members, key=lambda m: (m[1].link is None, m[1].rank, m[0])
    )[1]

    dates = sorted({d for d, _ in members})
    outlets: list[str] = []
    for _, headline in members:
        if headline.outlet not in outlets:
            outlets.append(headline.outlet)

    return Story(
        title=representative.title,
        link=representative.link,
        outlets=outlets,
        dates=dates,
        best_rank=min(headline.rank for _, headline in members),
        appearances=len(members),
    )


def rank_stories(stories: list[Story]) -> list[Story]:
    return sorted(
        stories,
        key=lambda s: (-len(s.dates), s.best_rank, -s.appearances, s.title),
    )


def retrospective_filename(latest: date) -> str:
    iso = latest.isocalendar()
    return f"retrospective-{iso.year:04d}-W{iso.week:02d}.md"


def _format_dates(dates: list[date]) -> str:
    return ", ".join(d.strftime("%b %d").replace(" 0", " ") for d in dates)


def render_retrospective(
    stories: list[Story],
    latest: date,
    span_start: date,
    digest_count: int,
) -> str:
    iso = latest.isocalendar()
    lines = [
        f"# Weekly Retrospective — {iso.year} W{iso.week:02d}",
        "",
        f"The stories from the last {digest_count} daily digest(s) "
        f"({span_start.isoformat()} to {latest.isoformat()}) that recurred across "
        "the most days. Recurrence is the durability signal — what still mattered "
        "over the week, not what went viral on any single day.",
        "",
    ]

    for i, story in enumerate(stories, start=1):
        day_count = len(story.dates)
        day_word = "day" if day_count == 1 else "days"
        meta = f"{day_count} {day_word} · {', '.join(story.outlets)}"
        if story.link:
            lines.append(f"{i}. [{story.title}]({story.link}) — {meta}")
        else:
            lines.append(f"{i}. {story.title} — {meta}")
        lines.append(f"   {_format_dates(story.dates)}")
        lines.append("")

    lines.append("## Note")
    lines.append("")
    lines.append(
        f"Built from {digest_count} daily digest(s). Ranking is heuristic — stories "
        "are clustered by headline-token overlap and ordered by how many distinct "
        "days they appeared, then by their best daily rank. Every item is a verbatim "
        "headline carried from a prior daily digest; nothing is rewritten or invented."
    )
    lines.append("")

    return "\n".join(lines)


def build_retrospective(
    repo_root: str,
    days: int = RETRO_DEFAULT_DAYS,
    top: int = RETRO_DEFAULT_TOP,
) -> RetroResult:
    files = find_recent_digests(repo_root, days=days)
    if not files:
        return RetroResult(digest_count=0, latest_date=None, span_start=None)

    dated_headlines: list[tuple[date, list[Headline]]] = []
    for digest in files:
        with open(digest.path, encoding="utf-8") as f:
            text = f.read()
        dated_headlines.append((digest.date, flatten_headlines(parse_digest(text))))

    latest = files[-1].date
    span_start = files[0].date
    stories = rank_stories(cluster_stories(dated_headlines))[:top]

    if not stories:
        return RetroResult(
            digest_count=len(files), latest_date=latest, span_start=span_start
        )

    markdown = render_retrospective(stories, latest, span_start, len(files))
    return RetroResult(
        digest_count=len(files),
        latest_date=latest,
        span_start=span_start,
        stories=stories,
        filename=retrospective_filename(latest),
        markdown=markdown,
    )
