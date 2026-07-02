# Next Session Prompt

Paste the block below at the start of any session to continue the ANN roadmap.
It is reusable — it always resumes at the next unfinished session in
`docs/CONTINUITY.md`. Optionally name a specific session (e.g. "work Session 5")
to override the default of "next unfinished."

---

```
We are continuing work on ANN (All the News You Need) at
~/Desktop/development/ANN/. Follow the session-start ritual before writing any
code:

1. Read docs/CONTINUITY.md — this is the roadmap. Sessions 4-9 each define a
   self-contained unit of work with Goal, Files, Tasks, and Acceptance criteria.
2. Read this file (docs/NEXT_SESSION_PROMPT.md).
3. Run `git status` and `git log --oneline -5` to confirm a clean tree and see
   recent work.

Then:

4. Select the next unfinished session in docs/CONTINUITY.md (lowest-numbered
   session whose task checkboxes are not all checked), unless I named a specific
   session above.
5. Briefly restate that session's Goal and Acceptance criteria, and give me a
   short plan before implementing. If the session begins with a spike (e.g.
   Session 5), timebox the spike and report findings before committing to full
   implementation.
6. Implement the tasks.

Definition of done for the session (all required before you say it is complete):
- All of the session's Acceptance criteria are met.
- Tests pass at or above the current count. IMPORTANT: run tests with
  `.venv/bin/python -m pytest` — the system Python 3.14 lacks feedparser.
- `.venv/bin/ruff check .` is clean.
- New behavior ships with tests (pure functions / mocked network — do not add
  live-network or live-model tests).
- CHANGELOG.md updated under [Unreleased].
- docs/CONTINUITY.md updated: check the session's task boxes and note the commit
  hash; prune any docs/DEVELOPMENT.md R&D item that is now shipped.
- memory/ann_status.md updated with the new state.
- The session's work is committed. Every session ends with a commit (clear
  message + Co-Authored-By trailer); record its hash in docs/CONTINUITY.md.

Constraints and house rules:
- Preserve the no-fabrication guarantee: the model selects headlines by index
  only; never invent or rewrite headline text.
- No comments unless the WHY is non-obvious; no docstrings for internal
  functions; no emoji in files or commits.
- Prefer Edit over Write for existing files. Only modify files within
  ~/Desktop/development/ANN/.
- Never run `source .env`; never print or commit secrets; never `git add` .env.
- Commit at the end of every session with a clear message ending in the
  Co-Authored-By trailer. Push to origin main when I confirm.

Report the plan first, then proceed.
```

---

## Notes for the human

- This prompt auto-advances: it always targets the next unfinished session, so
  you can paste the same block every session.
- To jump to a specific track, add a line above the block, e.g.
  "Work Session 7 (extra outlets) this session."
- After each session completes and is committed, the checked boxes and commit
  hash in `docs/CONTINUITY.md` are what let the next paste resume correctly —
  so keep that file honest.
