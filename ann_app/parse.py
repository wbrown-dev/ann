from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field

from ann_app.config import OUTLET_FEEDS

_LINKED_ITEM = re.compile(r"^\d+\.\s+\[(?P<title>.+?)\]\((?P<link>[^)]+)\)\s*$")
_PLAIN_ITEM = re.compile(r"^\d+\.\s+(?P<title>.+?)\s*$")
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
                    link=linked.group("link").strip(),
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


def flatten_headlines(sections: list[OutletSection]) -> list[Headline]:
    return [h for section in sections for h in section.headlines]


def find_latest_digest(repo_root: str) -> str | None:
    matches = glob.glob(os.path.join(repo_root, "headlines-*.md"))
    if not matches:
        return None
    return max(matches, key=os.path.basename)
