# Next Session Prompt

Paste the block below to resume ANN work after the completed roadmap.

```
We are continuing work on ANN (All the News You Need) at
~/Desktop/development/ANN/. Follow the session-start ritual before writing code:

1. Read docs/CONTINUITY.md for the current state, shipped sessions, next phase,
   invariants, verification baseline, and open ideas.
2. Read docs/DEVELOPMENT.md and docs/ARCHITECTURE.md if the work touches code.
3. Run `git status` and `git log --oneline -5`.
4. Restate the requested goal, note the relevant invariant(s), and give a short
   plan before implementation.

Definition of done:
- The requested behavior is implemented and documented where appropriate.
- New behavior has focused tests using pure functions or mocked boundaries; do
  not add live-network or live-model tests.
- `.venv/bin/python -m pytest` passes (baseline: 133).
- `.venv/bin/ruff check .` is clean.
- CHANGELOG.md is updated under [Unreleased].
- docs/CONTINUITY.md and memory/ann_status.md reflect the new state when the
  project state changes.
- Work is committed with a clear message and a Co-Authored-By trailer; push to
  origin main only after confirmation.

House rules:
- Preserve no fabrication: the model selects headlines by index only.
- Never run `source .env`; never print or commit secrets; never `git add .env`.
- Only modify files within ~/Desktop/development/ANN/.
- Never interpolate untrusted values into a <script> block with plain
  json.dumps; use streamlit_app._script_json.
- Tests touching ann.run must patch both ann.REPO_ROOT and ann.DIGEST_DIR.
- Keep the image immutable: no source bind-mount over /app, no dev tooling.
```

The Sessions 4-14 roadmap is complete and archived in Git history. ANN is
production-ready as of v0.4.0: the security review is closed, the container is
hardened and verified, and CI gates lint, tests, `pip-audit`, and container
invariants. No next phase is currently selected; see docs/CONTINUITY.md open
ideas (Actions SHA pinning, GHCR publishing).
