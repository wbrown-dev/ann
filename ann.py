from __future__ import annotations

import argparse
import os
import sys
from datetime import date

from ann_app.cache import CacheError, load_candidates, save_candidates
from ann_app.config import SUPPORTED_MODEL_PROVIDERS, resolve_model_settings
from ann_app.fetch import fetch_all
from ann_app.filter import FilterError, select_headlines
from ann_app.render import render_markdown, update_readme_link
from ann_app.resolve import resolve_selection
from ann_app.retrospective import (
    RETRO_DEFAULT_DAYS,
    RETRO_DEFAULT_TOP,
    RETRO_MIN_DIGESTS,
    build_retrospective,
)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def run(
    target_date: date,
    dry_run: bool,
    within_hours: int,
    use_cache: bool = False,
    save_cache: bool = False,
    model_provider: str | None = None,
    model: str | None = None,
) -> int:
    if use_cache:
        try:
            candidates = load_candidates(target_date)
        except CacheError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        errors: dict[str, str] = {}
        print(f"Loaded {len(candidates)} candidates from cache.")
    else:
        print(f"Fetching candidate headlines (lookback {within_hours}h)...")
        fetch_result = fetch_all(within_hours=within_hours)
        candidates = fetch_result.candidates
        errors = fetch_result.errors
        print(f"Fetched {len(candidates)} candidates.")
        for outlet, error in errors.items():
            print(f"  warning: {outlet} — {error}")
        if save_cache:
            path = save_candidates(candidates, target_date)
            print(f"Saved candidate cache to {path}")

    try:
        resolved_provider, resolved_model = resolve_model_settings(model_provider, model)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        "Selecting headlines against the significance standard "
        f"with {resolved_provider}:{resolved_model}..."
    )
    try:
        selections = select_headlines(
            candidates,
            provider=resolved_provider,
            model=resolved_model,
        )
    except FilterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if sum(len(picks) for picks in selections.values()) == 0:
        print(
            "error: no headlines selected; refusing to write an empty digest",
            file=sys.stderr,
        )
        return 2

    print("Resolving publisher URLs...")
    resolve_selection(selections)

    markdown = render_markdown(selections, errors)

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


def retro(
    days: int,
    top: int,
    dry_run: bool,
    rerank_model: bool = False,
    model_provider: str | None = None,
    model: str | None = None,
) -> int:
    if rerank_model:
        try:
            resolved_provider, resolved_model = resolve_model_settings(model_provider, model)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(
            "Re-ranking retrospective stories by index "
            f"with {resolved_provider}:{resolved_model}..."
        )
    else:
        resolved_provider = None
        resolved_model = None

    try:
        result = build_retrospective(
            REPO_ROOT,
            days=days,
            top=top,
            rerank=rerank_model,
            provider=resolved_provider,
            model=resolved_model,
        )
    except FilterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if result.digest_count < RETRO_MIN_DIGESTS:
        print(
            f"error: found {result.digest_count} recent digest(s); need at least "
            f"{RETRO_MIN_DIGESTS} to build a retrospective",
            file=sys.stderr,
        )
        return 2

    if not result.stories:
        print(
            "error: no recurring stories found; refusing to write an empty retrospective",
            file=sys.stderr,
        )
        return 2

    if dry_run:
        print(f"\n--- {result.filename} (dry run, not written) ---\n")
        print(result.markdown)
        return 0

    out_path = os.path.join(REPO_ROOT, result.filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.markdown)
    print(f"Wrote {out_path}")

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
    run_parser.add_argument(
        "--model-provider",
        choices=SUPPORTED_MODEL_PROVIDERS,
        default=None,
        help="Model provider to use for index selection (default: ANN_MODEL_PROVIDER or anthropic).",
    )
    run_parser.add_argument(
        "--model",
        default=None,
        help="Model name to use for index selection (default: ANN_MODEL or provider default).",
    )
    cache_group = run_parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--save-cache",
        action="store_true",
        help="Save fetched candidates to a dated snapshot for later offline replay.",
    )
    cache_group.add_argument(
        "--use-cache",
        action="store_true",
        help="Load candidates from the dated cache snapshot instead of fetching feeds.",
    )

    retro_parser = subparsers.add_parser(
        "retro",
        help="Build a weekly retrospective from recent daily digests.",
    )
    retro_parser.add_argument(
        "--days",
        type=int,
        default=RETRO_DEFAULT_DAYS,
        help=f"Look back this many days of digests (default: {RETRO_DEFAULT_DAYS}).",
    )
    retro_parser.add_argument(
        "--top",
        type=int,
        default=RETRO_DEFAULT_TOP,
        help=f"Include at most this many stories (default: {RETRO_DEFAULT_TOP}).",
    )
    retro_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the retrospective instead of writing it.",
    )
    retro_parser.add_argument(
        "--rerank-model",
        action="store_true",
        help="Optionally re-rank clustered stories with the configured model, by index only.",
    )
    retro_parser.add_argument(
        "--model-provider",
        choices=SUPPORTED_MODEL_PROVIDERS,
        default=None,
        help="Model provider for --rerank-model (default: ANN_MODEL_PROVIDER or anthropic).",
    )
    retro_parser.add_argument(
        "--model",
        default=None,
        help="Model name for --rerank-model (default: ANN_MODEL or provider default).",
    )

    args = parser.parse_args()

    if args.command == "run":
        return run(
            args.date,
            args.dry_run,
            args.within_hours,
            use_cache=args.use_cache,
            save_cache=args.save_cache,
            model_provider=args.model_provider,
            model=args.model,
        )

    if args.command == "retro":
        return retro(
            args.days,
            args.top,
            args.dry_run,
            rerank_model=args.rerank_model,
            model_provider=args.model_provider,
            model=args.model,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
