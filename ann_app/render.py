from __future__ import annotations

from ann_app.config import OUTLET_DISPLAY_NAMES, OUTLET_FEEDS
from ann_app.fetch import Candidate


def render_markdown(
    selections: dict[str, list[Candidate]],
    fetch_errors: dict[str, str],
) -> str:
    lines: list[str] = []

    for outlet in OUTLET_FEEDS:
        display_name = OUTLET_DISPLAY_NAMES.get(outlet, outlet)
        lines.append(f"## {display_name}")
        lines.append("")

        headlines = selections.get(outlet, [])
        if headlines:
            for i, c in enumerate(headlines, start=1):
                lines.append(f"{i}. [{c.title}]({c.link})")
        else:
            lines.append("No headlines available for this outlet today.")
        lines.append("")

    notes = []
    for outlet in OUTLET_FEEDS:
        error = fetch_errors.get(outlet)
        count = len(selections.get(outlet, []))
        if error:
            notes.append(f"- **{outlet}** — feed fetch issue: {error}")
        elif count < 5:
            notes.append(f"- **{outlet}** — only {count} usable headline(s) found within the lookback window.")

    lines.append("## Note")
    lines.append("")
    if notes:
        lines.extend(notes)
    else:
        lines.append("No access limitations encountered this session.")
    lines.append("")

    return "\n".join(lines)


def update_readme_link(readme_path: str, filename: str) -> None:
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()

    old_line_prefix = "[Go to Today's Headlines.]"
    new_line = f"[Go to Today's Headlines.]({filename})"

    lines = content.splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(old_line_prefix):
            lines[i] = new_line
            replaced = True
            break

    if not replaced:
        raise ValueError("could not find 'Go to Today's Headlines.' link in README.md")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
