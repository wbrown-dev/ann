# ANN Status

Last updated: 2026-07-02

Sessions 4-13 are shipped. Session 12 added optional provider-assisted
retrospective re-ranking by story index. Session 13 prepared ANN for a v0.2.0
release.

Current state:
- Daily digest pipeline is complete: fetch -> provider index-only filter ->
  render -> latest Markdown digest -> Streamlit dashboard.
- GitHub Actions can run the daily digest on schedule or manual dispatch.
- Selected AP Google News links resolve best-effort to canonical publisher URLs.
- Candidate caching supports deterministic offline replay.
- Optional extra outlets are available via `ANN_EXTRA_OUTLETS`.
- `ann.py retro` builds a deterministic weekly retrospective from prior
  digests by default. Add `--rerank-model` to re-rank clustered stories with the
  configured provider using only returned story indices.
- The dashboard has daily digest and weekly retrospective tabs, auto-checks the
  latest generated files every 30 seconds, and reruns when filename or mtime
  changes.
- `ANN_MODEL_PROVIDER` / `--model-provider` can select Anthropic or OpenAI;
  `ANN_MODEL` / `--model` selects the model. Keys remain env/deployment secret
  only (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`) and are never persisted.
- The completed Sessions 4-13 roadmap has been compressed into a final-state
  continuity archive for post-roadmap work.
- Release hardening is in place for v0.2.0: project metadata is bumped,
  changelog entries are under a dated `0.2.0` section, production setup and
  release steps are documented, and blank GitHub Actions model variables fall
  back to defaults.

Quality gate:
- `.venv/bin/python -m pytest`: 83 passed.
- `.venv/bin/ruff check .`: clean.

Open R&D:
- Additional providers behind the same normalized index-only interface.
