# ANN Status

Last updated: 2026-07-02 (v0.3.0: Gemini provider)

Sessions 4-13 are shipped. Session 13 prepared ANN for a v0.2.0 release.
Post-roadmap v0.3.0: added Google Gemini as a third index-only model provider
and disabled Gemini thinking for selection reliability.

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
- `ANN_MODEL_PROVIDER` / `--model-provider` can select Anthropic, OpenAI, or
  Gemini; `ANN_MODEL` / `--model` selects the model. Keys remain env/deployment
  secret only (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY` /
  `GOOGLE_API_KEY`) and are never persisted. Gemini default: `gemini-2.5-flash`.
- Gemini is fully wired into ops: the daily-digest GitHub Actions workflow
  validates the `gemini` provider and injects `GEMINI_API_KEY` / `GOOGLE_API_KEY`
  secrets, and DEVOPS.md / DEVELOPMENT.md document the Gemini secret, repo
  variable, and Docker invocation. Removed the orphaned `headlines20260701.md`
  (malformed name from a manual upload; matched no `headlines-*.md` glob).
- Gemini thinking is disabled (`thinking_config.thinking_budget = 0`) so
  `gemini-2.5-flash` reasoning tokens cannot exhaust `max_output_tokens` and
  return empty selection text. Released as v0.3.0.
- The completed Sessions 4-13 roadmap has been compressed into a final-state
  continuity archive for post-roadmap work.
- Release hardening is in place for v0.2.0: project metadata is bumped,
  changelog entries are under a dated `0.2.0` section, production setup and
  release steps are documented, and blank GitHub Actions model variables fall
  back to defaults.

Quality gate:
- `.venv/bin/python -m pytest`: 88 passed.
- `.venv/bin/ruff check .`: clean.

Open R&D:
- Additional providers behind the same normalized index-only interface.

Next session — Security review (not yet done):
- No dedicated security eval performed. Incidental scan found injection surface
  handled (`_safe_url` scheme allowlist + title escaping, no exec sinks,
  env-only secrets, least-privilege CI). Eval should still cover: SSRF host
  allowlist in `resolve.py`, feedparser XXE posture, `pip-audit` + action/dep
  pinning, and security regression tests for `_safe_url`/escaping. See
  `docs/CONTINUITY.md` "Security Review".
