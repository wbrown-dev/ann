# ANN Status

Last updated: 2026-07-02

Sessions 4-11 are shipped. Session 11 added a Streamlit dashboard tab for the
latest weekly retrospective alongside the daily headline rotation.

Current state:
- Daily digest pipeline is complete: fetch -> provider index-only filter ->
  render -> latest Markdown digest -> Streamlit dashboard.
- GitHub Actions can run the daily digest on schedule or manual dispatch.
- Selected AP Google News links resolve best-effort to canonical publisher URLs.
- Candidate caching supports deterministic offline replay.
- Optional extra outlets are available via `ANN_EXTRA_OUTLETS`.
- `ann.py retro` builds a deterministic weekly retrospective from prior
  digests.
- The dashboard has daily digest and weekly retrospective tabs, auto-checks the
  latest generated files every 30 seconds, and reruns when filename or mtime
  changes.
- `ANN_MODEL_PROVIDER` / `--model-provider` can select Anthropic or OpenAI;
  `ANN_MODEL` / `--model` selects the model. Keys remain env/deployment secret
  only (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`) and are never persisted.
- The completed Sessions 4-10 roadmap has been compressed into a final-state
  continuity archive for post-roadmap work.

Quality gate:
- `.venv/bin/python -m pytest`: 75 passed.
- `.venv/bin/ruff check .`: clean.

Open R&D:
- Optional model-assisted retrospective re-ranking, index-only.
- Additional providers behind the same normalized index-only interface.
