from __future__ import annotations

import json
import re
from collections import defaultdict

import anthropic

from ann_app.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    HEADLINES_PER_OUTLET,
    SELECTION_STANDARD,
)
from ann_app.fetch import Candidate

MAX_CANDIDATES_PER_OUTLET = 40


class FilterError(RuntimeError):
    pass


def _build_prompt(grouped: dict[str, list[Candidate]]) -> str:
    sections = []
    for outlet, candidates in grouped.items():
        lines = [f"## {outlet}"]
        for i, c in enumerate(candidates[:MAX_CANDIDATES_PER_OUTLET]):
            summary = f" — {c.summary}" if c.summary else ""
            lines.append(f"{i}. {c.title}{summary}")
        sections.append("\n".join(lines))

    candidate_block = "\n\n".join(sections)

    return f"""You are curating a daily news digest. Below is the selection \
standard you must apply, followed by candidate headlines grouped by outlet. \
Each candidate is numbered starting at 0.

SELECTION STANDARD:
{SELECTION_STANDARD}

For each outlet, choose exactly {HEADLINES_PER_OUTLET} candidates by their \
number, ranked most significant first, applying the standard above. Only \
select from the numbered candidates given — do not invent headlines. If an \
outlet has fewer than {HEADLINES_PER_OUTLET} usable candidates, return as \
many as are usable.

CANDIDATES:
{candidate_block}

Respond with ONLY a JSON object mapping each outlet name to a list of chosen \
candidate numbers in ranked order, e.g.:
{{"WSJ": [3, 0, 12, 7, 21], "NYT": [...], "NBC": [...], "AP": [...]}}
"""


_CODE_FENCE = re.compile(r"```(?:json)?\s*(?P<body>.*?)```", re.DOTALL)


def _parse_response(text: str) -> dict[str, list[int]]:
    stripped = text.strip()

    fence = _CODE_FENCE.search(stripped)
    if fence:
        stripped = fence.group("body").strip()

    # Fall back to the first {...} object if the model wrapped the JSON in prose.
    candidate = stripped
    if not candidate.startswith("{"):
        brace = re.search(r"\{.*\}", stripped, re.DOTALL)
        if brace:
            candidate = brace.group(0)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise FilterError(f"could not parse model response as JSON: {exc}\n{text}") from exc


def select_headlines(candidates: list[Candidate]) -> dict[str, list[Candidate]]:
    if not ANTHROPIC_API_KEY:
        raise FilterError("ANTHROPIC_API_KEY is not set")

    grouped: dict[str, list[Candidate]] = defaultdict(list)
    for c in candidates:
        grouped[c.outlet].append(c)

    if not grouped:
        return {}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = _build_prompt(grouped)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    selections = _parse_response(text)

    result: dict[str, list[Candidate]] = {}
    for outlet, candidates_for_outlet in grouped.items():
        indices = selections.get(outlet, [])
        chosen = []
        for idx in indices[:HEADLINES_PER_OUTLET]:
            if isinstance(idx, int) and 0 <= idx < len(candidates_for_outlet):
                chosen.append(candidates_for_outlet[idx])
        result[outlet] = chosen

    return result
