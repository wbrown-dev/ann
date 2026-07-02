from __future__ import annotations

import argparse
import os
import sys
from datetime import date

from ann_app.fetch import fetch_all
from ann_app.filter import FilterError, select_headlines
from ann_app.render import render_markdown, update_readme_link

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def run(target_date: date, dry_run: bool, within_hours: int) -> int:
    print(f"Fetching candidate headlines (lookback {within_hours}h)...")
    fetch_result = fetch_all(within_hours=within_hours)
    print(f"Fetched {len(fetch_result.candidates)} candidates.")
    for outlet, error in fetch_result.errors.items():
        print(f"  warning: {outlet} — {error}")

    print("Selecting headlines against the significance standard...")
    try:
        selections = select_headlines(fetch_result.candidates)
    except FilterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if sum(len(picks) for picks in selections.values()) == 0:
        print(
            "error: no headlines selected; refusing to write an empty digest",
            file=sys.stderr,
        )
        return 2

    markdown = render_markdown(selections, fetch_result.errors)

    filename = f"headlines-{target_date.isoformat()}.md"
    out_path = os.path.join(REPO_ROOT, filename)

    if dry_run:
        print(f"\n--- {filename} (dry run, not written) ---\n")
        print(markdown)
        return 0

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"Wrote {out_path}")

    readme_path = os.path.join(REPO_ROOT, "README.md")
    update_readme_link(readme_path, filename)
    print(f"Updated {readme_path}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the daily ANN headlines digest.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Fetch, filter, and write today's digest.")
    run_parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today(),
        help="Date to generate the digest for (YYYY-MM-DD). Defaults to today.",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the digest instead of writing it and updating README.md.",
    )
    run_parser.add_argument(
        "--within-hours",
        type=int,
        default=36,
        help="Only consider candidate headlines published within this many hours (default: 36).",
    )

    args = parser.parse_args()

    if args.command == "run":
        return run(args.date, args.dry_run, args.within_hours)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
