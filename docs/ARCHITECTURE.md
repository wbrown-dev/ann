# Architecture

ANN is a small pipeline plus two front-ends (a CLI and a Streamlit dashboard)
over the same core package, `ann_app`.

```
RSS / Google News            ann_app/fetch.py      -> Candidate[]
        │                          │
        ▼                          ▼
  ann_app/config.py  ──────►  ann_app/filter.py    -> {outlet: Candidate[]}   (Claude selects by index)
                                   │
                                   ▼
                            ann_app/render.py       -> headlines-YYYY-MM-DD.md
                                   │
             ┌─────────────────────┴─────────────────────┐
             ▼                                            ▼
        ann.py (CLI)                            ann_app/parse.py
     writes the digest                    reads a digest back into
     and updates README                   typed Headline objects
                                                  │
                                                  ▼
                                          streamlit_app.py
                                    rotating headline dashboard
```

## Modules

| Module | Responsibility |
| --- | --- |
| `ann_app/config.py` | Outlet → RSS feed map, the selection standard, model + request settings. |
| `ann_app/fetch.py` | Pull and de-duplicate candidate headlines within a lookback window. |
| `ann_app/filter.py` | Ask Claude to rank the top 5 per outlet **by candidate index only**, so titles and links are never fabricated. |
| `ann_app/render.py` | Render selections to the daily Markdown digest and update the README link. |
| `ann_app/parse.py` | Parse a digest Markdown file back into typed `OutletSection`/`Headline` objects; locate the newest digest. |
| `ann.py` | CLI entry point (`run`, `--dry-run`, `--within-hours`, `--date`). |
| `streamlit_app.py` | Dashboard front-end (see below). |

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
