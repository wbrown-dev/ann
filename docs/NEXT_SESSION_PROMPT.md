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
- `.venv/bin/python -m pytest` passes.
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
```

The original Sessions 4-11 roadmap is complete and archived in Git history.
The current next-phase item is Session 12: optional model-assisted
retrospective re-ranking, index-only.
