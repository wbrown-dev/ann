# ANN Status

Last updated: 2026-07-02

Sessions 4-9 are shipped. Current implementation commit: `cb41081`
(`feat: auto-refresh dashboard digest`).
Documentation finalization is captured in the latest docs commit.

Current state:
- Daily digest pipeline is complete: fetch -> Claude index-only filter ->
  render -> latest Markdown digest -> Streamlit dashboard.
- GitHub Actions can run the daily digest on schedule or manual dispatch.
- Selected AP Google News links resolve best-effort to canonical publisher URLs.
- Candidate caching supports deterministic offline replay.
- Optional extra outlets are available via `ANN_EXTRA_OUTLETS`.
- `ann.py retro` builds a deterministic weekly retrospective from prior
  digests.
- The dashboard auto-checks for a changed latest digest every 30 seconds and
  reruns when the filename or mtime changes.
- The completed Sessions 4-9 roadmap has been compressed into a final-state
  continuity archive for post-roadmap work.

Quality gate:
- `.venv/bin/python -m pytest`: 62 passed.
- `.venv/bin/ruff check .`: clean.

Open R&D:
- Optional model-assisted retrospective re-ranking, index-only.
- Dashboard tab for the latest retrospective.
