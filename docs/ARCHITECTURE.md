# Architecture

ANN is a small pipeline plus two front-ends (CLI and Streamlit dashboard) over
the same core package, `ann_app`.

```
RSS / Google News -> fetch/cache -> Claude index selection -> resolve AP URLs
                                      │
                                      ▼
                          render headlines-YYYY-MM-DD.md
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
              ann.py commands                    streamlit_app.py
         run daily digest / retro           rotating auto-refresh dashboard
```

## Modules

| Module | Responsibility |
| --- | --- |
| `ann_app/config.py` | Outlet feeds, display names, accents, selection standard, model settings. |
| `ann_app/fetch.py` | Pull and de-duplicate candidate headlines within a lookback window. |
| `ann_app/cache.py` | Save/load versioned candidate snapshots for offline replay. |
| `ann_app/filter.py` | Ask Claude to rank by candidate index only, so titles and links are never fabricated. |
| `ann_app/resolve.py` | Best-effort resolution of selected AP Google News links to canonical publisher URLs. |
| `ann_app/render.py` | Render selections to daily Markdown and update the README link. |
| `ann_app/parse.py` | Parse digest Markdown into typed sections/headlines and locate the latest digest. |
| `ann_app/retrospective.py` | Build deterministic weekly retrospectives from prior daily digests. |
| `ann.py` | CLI entry point for `run` and `retro`. |
| `streamlit_app.py` | Rotating dashboard that auto-detects changed digest files. |

## Selection standard

Headlines are chosen for **significance, not virality** — whether a story is
likely to still matter in 30 days. The full rubric lives in
`ann_app/config.py` (`SELECTION_STANDARD`) and is passed to the model verbatim.

## No-fabrication guarantee

The model only ever returns **candidate indices**. The actual title and URL are
looked up from the fetched `Candidate` list, so the digest can never contain a
headline or link the model invented. Where a source URL cannot be confirmed,
the digest carries a cross-verified summary with no link, and the parser marks
it as `link = None`.

## Streamlit dashboard

`streamlit_app.py` loads the latest digest, flattens all headlines across
outlets, and hands them to a self-contained HTML/JS component:

- The component **shuffles** the full set and shows one headline at a time.
- Each headline is displayed for **10 seconds** (a progress bar tracks the
  interval), then it advances.
- Every headline is shown **once before any repeats**; when the set is
  exhausted the component reshuffles and continues.
- Each outlet has an accent color (WSJ cyan, NYT blue, NBC indigo, AP magenta)
  matching the dark "ANN" visual system.
- A timed Streamlit fragment checks the latest digest filename and mtime every
  30 seconds and reruns when a new or overwritten digest appears.
