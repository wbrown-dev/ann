from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field

from ann_app.config import OUTLET_FEEDS

_LINKED_ITEM = re.compile(r"^\d+\.\s+\[(?P<title>.+?)\]\((?P<link>[^)]+)\)\s*$")
_PLAIN_ITEM = re.compile(r"^\d+\.\s+(?P<title>.+?)\s*$")
_RETRO_LINKED_ITEM = re.compile(
    r"^\d+\.\s+\[(?P<title>.+?)\]\((?P<link>[^)]+)\)\s+—\s+(?P<meta>.+?)\s*$"
)
_RETRO_PLAIN_ITEM = re.compile(r"^\d+\.\s+(?P<title>.+)\s+—\s+(?P<meta>.+?)\s*$")
_SECTION = re.compile(r"^##\s+(?P<name>.+?)\s*$")

_KNOWN_OUTLETS = set(OUTLET_FEEDS)


@dataclass
class Headline:
    outlet: str
    rank: int
    title: str
    link: str | None = None


@dataclass
class OutletSection:
    outlet: str
    headlines: list[Headline] = field(default_factory=list)
    note: str | None = None


@dataclass(frozen=True)
class DigestState:
    path: str
    mtime_ns: int


@dataclass
class RetrospectiveItem:
    rank: int
    title: str
    meta: str
    dates: str | None = None
    link: str | None = None


@dataclass
class Retrospective:
    title: str
    intro: str
    items: list[RetrospectiveItem] = field(default_factory=list)
    note: str | None = None


def _clean_markdown_link(raw: str) -> str:
    link = raw.strip()
    if link.startswith("<") and link.endswith(">"):
        return link[1:-1].strip()
    return link


def parse_digest(text: str) -> list[OutletSection]:
    """Parse a headlines-YYYY-MM-DD.md digest into structured outlet sections.

    Numbered items may be linked (``1. [Title](url)``) or plain summaries
    (``1. Title``) when a source URL could not be confirmed. Trailing prose
    ``Note:`` lines and the final ``## Note`` section are ignored.
    """
    sections: dict[str, OutletSection] = {}
    current: OutletSection | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        section_match = _SECTION.match(line)
        if section_match:
            name = section_match.group("name").strip()
            if name in _KNOWN_OUTLETS:
                current = sections.setdefault(name, OutletSection(outlet=name))
            else:
                current = None
            continue

        if current is None:
            continue

        linked = _LINKED_ITEM.match(line)
        if linked:
            current.headlines.append(
                Headline(
                    outlet=current.outlet,
                    rank=len(current.headlines) + 1,
                    title=linked.group("title").strip(),
                    link=_clean_markdown_link(linked.group("link")),
                )
            )
            continue

        plain = _PLAIN_ITEM.match(line)
        if plain:
            current.headlines.append(
                Headline(
                    outlet=current.outlet,
                    rank=len(current.headlines) + 1,
                    title=plain.group("title").strip(),
                    link=None,
                )
            )

    # Preserve the outlet order declared in config.
    return [sections[o] for o in OUTLET_FEEDS if o in sections]


def parse_retrospective(text: str) -> Retrospective:
    """Parse a retrospective-YYYY-Www.md file into display-ready items.

    Retrospective items are already generated from prior digests, so this parser
    only extracts existing titles, links, metadata, and date lines. It does not
    rewrite or infer story text.
    """
    lines = text.splitlines()
    title = ""
    intro_lines: list[str] = []
    note_lines: list[str] = []
    items: list[RetrospectiveItem] = []
    in_note = False
    last_item: RetrospectiveItem | None = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
            continue

        if stripped == "## Note":
            in_note = True
            last_item = None
            continue

        if in_note:
            note_lines.append(stripped)
            continue

        linked = _RETRO_LINKED_ITEM.match(stripped)
        plain = _RETRO_PLAIN_ITEM.match(stripped)
        if linked:
            last_item = RetrospectiveItem(
                rank=len(items) + 1,
                title=linked.group("title").strip(),
                link=linked.group("link").strip(),
                meta=linked.group("meta").strip(),
            )
            items.append(last_item)
            continue
        if plain:
            last_item = RetrospectiveItem(
                rank=len(items) + 1,
                title=plain.group("title").strip(),
                meta=plain.group("meta").strip(),
            )
            items.append(last_item)
            continue

        if last_item is not None and line.startswith("   "):
            last_item.dates = stripped
            continue

        if not items:
            intro_lines.append(stripped)

    return Retrospective(
        title=title,
        intro=" ".join(intro_lines),
        items=items,
        note=" ".join(note_lines) if note_lines else None,
    )


def flatten_headlines(sections: list[OutletSection]) -> list[Headline]:
    return [h for section in sections for h in section.headlines]


def find_latest_digest(repo_root: str) -> str | None:
    state = find_latest_digest_state(repo_root)
    return state.path if state else None


def find_latest_digest_state(repo_root: str) -> DigestState | None:
    matches = glob.glob(os.path.join(repo_root, "headlines-*.md"))
    return _latest_markdown_state(matches)


def find_latest_retrospective(repo_root: str) -> str | None:
    state = find_latest_retrospective_state(repo_root)
    return state.path if state else None


def find_latest_retrospective_state(repo_root: str) -> DigestState | None:
    matches = glob.glob(os.path.join(repo_root, "retrospective-*.md"))
    return _latest_markdown_state(matches)


def _latest_markdown_state(matches: list[str]) -> DigestState | None:
    if not matches:
        return None
    latest = max(matches, key=os.path.basename)
    return DigestState(path=latest, mtime_ns=os.stat(latest).st_mtime_ns)
