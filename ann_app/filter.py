from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from ann_app.config import (
    HEADLINES_PER_OUTLET,
    MODEL_NAME,
    SELECTION_STANDARD,
    resolve_model_settings,
)
from ann_app.fetch import Candidate
from ann_app.providers import ModelProvider, ProviderError, build_provider

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
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise FilterError(f"could not parse model response as JSON: {exc}\n{text}") from exc

    return _validate_response(parsed)


def _validate_response(parsed: Any) -> dict[str, list[int]]:
    if not isinstance(parsed, dict):
        raise FilterError("model response must be a JSON object mapping outlet names to index lists")

    selections: dict[str, list[int]] = {}
    for outlet, indices in parsed.items():
        if not isinstance(outlet, str):
            raise FilterError("model response outlet names must be strings")
        if not isinstance(indices, list):
            raise FilterError(f"model response for {outlet} must be a list of candidate indices")
        selections[outlet] = indices

    return selections


def select_headlines(
    candidates: list[Candidate],
    client: object | None = None,
    provider: str | ModelProvider | None = None,
    model: str | None = None,
) -> dict[str, list[Candidate]]:
    grouped: dict[str, list[Candidate]] = defaultdict(list)
    for c in candidates:
        grouped[c.outlet].append(c)

    if not grouped:
        return {}

    prompt = _build_prompt(grouped)
    model_provider, model_name = _resolve_provider(provider, model, client)
    try:
        text = model_provider.complete(prompt, model_name)
    except ProviderError as exc:
        raise FilterError(str(exc)) from exc
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


def _resolve_provider(
    provider: str | ModelProvider | None,
    model: str | None,
    client: object | None,
) -> tuple[ModelProvider, str]:
    if provider is not None and not isinstance(provider, str):
        model_name = (model or MODEL_NAME).strip()
        if not model_name:
            raise FilterError("model name cannot be empty")
        return provider, model_name

    try:
        provider_name, model_name = resolve_model_settings(provider, model)
    except ValueError as exc:
        raise FilterError(str(exc)) from exc

    return build_provider(provider_name, client=client), model_name
