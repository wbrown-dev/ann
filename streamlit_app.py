from __future__ import annotations

import html
import json
import os

import streamlit as st
import streamlit.components.v1 as components

from ann_app.config import OUTLET_ACCENTS
from ann_app.parse import (
    find_latest_digest,
    find_latest_digest_state,
    find_latest_retrospective,
    find_latest_retrospective_state,
    flatten_headlines,
    parse_digest,
    parse_retrospective,
)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
ROTATION_SECONDS = 10
REFRESH_POLL_SECONDS = 30

DEFAULT_ACCENT = "#4dd0e1"
CONTENT_STATE_KEY = "ann_content_state"


def _safe_url(link: str | None) -> str | None:
    """Only allow http(s) links; drop javascript:/data: and other schemes."""
    if link and link.lower().startswith(("http://", "https://")):
        return link
    return None


st.set_page_config(
    page_title="ANN — All the News You Need",
    page_icon="🗞️",
    layout="wide",
    initial_sidebar_state="expanded",
)

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@500&display=swap');

:root {
  --ann-bg-1: #151a2b;
  --ann-panel: rgba(22, 26, 46, 0.82);
  --ann-border: rgba(132, 132, 168, 0.26);
  --ann-text: #f5f7ff;
  --ann-text-soft: rgba(245, 247, 255, 0.65);
}

.stApp {
  background:
    radial-gradient(circle at 20% 5%, rgba(124, 77, 255, 0.35), transparent 38%),
    radial-gradient(circle at 90% 20%, rgba(80, 165, 255, 0.26), transparent 35%),
    radial-gradient(circle at 60% 100%, rgba(192, 132, 252, 0.16), transparent 30%),
    linear-gradient(135deg, var(--ann-bg-1), #0f1426 44%, #121833 100%);
  color: var(--ann-text);
  font-family: 'Manrope', 'Segoe UI', system-ui, sans-serif;
}

section[data-testid="stSidebar"] {
  background: rgba(15, 19, 36, 0.9);
  border-right: 1px solid var(--ann-border);
}

h1, h2, h3, h4 {
  font-family: 'Space Grotesk', 'Manrope', sans-serif !important;
  color: var(--ann-text) !important;
  letter-spacing: 0.01em;
}

.ann-kicker {
  font-family: 'Space Grotesk', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.32em;
  font-size: 0.72rem;
  color: var(--ann-text-soft);
}

.ann-outlet-card {
  background: var(--ann-panel);
  border: 1px solid var(--ann-border);
  border-radius: 16px;
  padding: 18px 20px;
  margin-bottom: 16px;
}
.ann-outlet-head {
  font-family: 'Space Grotesk', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-weight: 700;
  font-size: 1rem;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.ann-outlet-dot {
  width: 10px; height: 10px; border-radius: 50%;
}
.ann-item { margin: 8px 0; line-height: 1.45; }
.ann-rank {
  font-family: 'JetBrains Mono', monospace;
  color: var(--ann-text-soft);
  margin-right: 8px;
}
.ann-item a { color: var(--ann-text); text-decoration: none; }
.ann-item a:hover { text-decoration: underline; }
.ann-item.no-link { color: var(--ann-text-soft); }
.ann-retro-card {
  background: var(--ann-panel);
  border: 1px solid var(--ann-border);
  border-radius: 16px;
  padding: 18px 20px;
  margin-bottom: 14px;
}
.ann-retro-meta {
  color: var(--ann-text-soft);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  margin-top: 8px;
}
.ann-retro-card a { color: var(--ann-text); text-decoration: none; }
.ann-retro-card a:hover { text-decoration: underline; }

::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.7); }
::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #0ea5e9, #6366f1);
  border-radius: 8px;
}
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def _rotation_component(headlines: list[dict], accents: dict[str, str]) -> str:
    payload = json.dumps(headlines)
    accents_json = json.dumps(accents)
    return f"""
<div id="ann-hero"></div>
<style>
  #ann-hero {{
    font-family: 'Manrope', 'Segoe UI', system-ui, sans-serif;
    color: #f5f7ff;
  }}
  .hero-card {{
    position: relative;
    background: rgba(22, 26, 46, 0.82);
    border: 1px solid rgba(132, 132, 168, 0.26);
    border-radius: 22px;
    padding: 30px 34px 26px;
    min-height: 260px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
    box-shadow: 0 24px 60px rgba(6, 9, 22, 0.55);
  }}
  .hero-accent {{
    position: absolute; top: 0; left: 0; height: 100%; width: 6px;
    transition: background 0.6s ease;
  }}
  .hero-badge {{
    font-family: 'Space Grotesk', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-weight: 700;
    font-size: 0.82rem;
    padding: 5px 14px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    align-self: flex-start;
    border: 1px solid rgba(132, 132, 168, 0.3);
    transition: color 0.5s ease, border-color 0.5s ease;
  }}
  .hero-rank {{
    font-family: 'JetBrains Mono', monospace;
    color: rgba(245, 247, 255, 0.55);
    font-size: 0.8rem;
    margin-left: 10px;
  }}
  .hero-title {{
    font-family: 'Space Grotesk', 'Manrope', sans-serif;
    font-size: 1.7rem;
    line-height: 1.28;
    font-weight: 600;
    margin: 20px 0 14px;
    transition: opacity 0.45s ease, transform 0.45s ease;
  }}
  .hero-title a {{ color: #f5f7ff; text-decoration: none; }}
  .hero-title a:hover {{ text-decoration: underline; }}
  .hero-meta {{
    display: flex; align-items: center; justify-content: space-between;
    margin-top: auto;
  }}
  .hero-link {{
    font-size: 0.82rem;
    color: rgba(245, 247, 255, 0.55);
    font-family: 'JetBrains Mono', monospace;
    max-width: 60%;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }}
  .hero-count {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: rgba(245, 247, 255, 0.55);
  }}
  .hero-progress {{
    position: absolute; bottom: 0; left: 0; height: 4px; width: 0%;
    transition: width 0.2s linear;
  }}
  .fade-out {{ opacity: 0; transform: translateY(-8px); }}
</style>
<div class="hero-card">
  <div class="hero-accent" id="hero-accent"></div>
  <div>
    <span class="hero-badge" id="hero-badge">—</span>
    <span class="hero-rank" id="hero-rank"></span>
  </div>
  <div class="hero-title" id="hero-title">Loading headlines…</div>
  <div class="hero-meta">
    <div class="hero-link" id="hero-link"></div>
    <div class="hero-count" id="hero-count"></div>
  </div>
  <div class="hero-progress" id="hero-progress"></div>
</div>
<script>
(function() {{
  const items = {payload};
  const accents = {accents_json};
  const defaultAccent = "{DEFAULT_ACCENT}";
  const rotationMs = {ROTATION_SECONDS * 1000};

  const titleEl = document.getElementById('hero-title');
  const badgeEl = document.getElementById('hero-badge');
  const rankEl = document.getElementById('hero-rank');
  const linkEl = document.getElementById('hero-link');
  const countEl = document.getElementById('hero-count');
  const accentEl = document.getElementById('hero-accent');
  const progressEl = document.getElementById('hero-progress');

  if (!items.length) {{
    titleEl.textContent = 'No headlines available yet.';
    return;
  }}

  function shuffle(n) {{
    const arr = Array.from({{length: n}}, (_, i) => i);
    for (let i = arr.length - 1; i > 0; i--) {{
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }}
    return arr;
  }}

  let order = shuffle(items.length);
  let pos = 0;

  function render() {{
    const item = items[order[pos]];
    const accent = accents[item.outlet] || defaultAccent;

    titleEl.classList.add('fade-out');
    setTimeout(() => {{
      accentEl.style.background = accent;
      badgeEl.textContent = item.outlet;
      badgeEl.style.color = accent;
      badgeEl.style.borderColor = accent;
      rankEl.textContent = '#' + item.rank;
      const safeLink = (item.link && /^https?:\\/\\//i.test(item.link)) ? item.link : null;
      if (safeLink) {{
        titleEl.textContent = '';
        const a = document.createElement('a');
        a.href = safeLink;
        a.target = '_blank';
        a.rel = 'noopener';
        a.textContent = item.title;
        titleEl.appendChild(a);
        linkEl.textContent = safeLink.replace(/^https?:\\/\\//, '');
      }} else {{
        titleEl.textContent = item.title;
        linkEl.textContent = 'cross-verified summary — no source link';
      }}
      countEl.textContent = (pos + 1) + ' / ' + items.length;
      progressEl.style.background = accent;
      titleEl.classList.remove('fade-out');
    }}, 350);
  }}

  function advance() {{
    pos += 1;
    if (pos >= order.length) {{
      order = shuffle(items.length);   // reshuffle: no repeats until all shown
      pos = 0;
    }}
    render();
  }}

  // progress bar
  let elapsed = 0;
  setInterval(() => {{
    elapsed += 200;
    const pct = Math.min(100, (elapsed / rotationMs) * 100);
    progressEl.style.width = pct + '%';
    if (elapsed >= rotationMs) {{
      elapsed = 0;
      progressEl.style.width = '0%';
      advance();
    }}
  }}, 200);

  render();
}})();
</script>
"""


def _render_digest(sections) -> None:
    cols = st.columns(2)
    for i, section in enumerate(sections):
        accent = OUTLET_ACCENTS.get(section.outlet, DEFAULT_ACCENT)
        items_html = []
        for h in section.headlines:
            title = html.escape(h.title)
            link = _safe_url(h.link)
            if link:
                body = f'<a href="{html.escape(link, quote=True)}" target="_blank" rel="noopener">{title}</a>'
                cls = "ann-item"
            else:
                body = title
                cls = "ann-item no-link"
            items_html.append(f'<div class="{cls}"><span class="ann-rank">{h.rank:02d}</span>{body}</div>')
        if not items_html:
            items_html.append('<div class="ann-item no-link">No headlines for this outlet today.</div>')

        card = (
            f'<div class="ann-outlet-card">'
            f'<div class="ann-outlet-head">'
            f'<span class="ann-outlet-dot" style="background:{accent}"></span>{section.outlet}</div>'
            f'{"".join(items_html)}</div>'
        )
        cols[i % 2].markdown(card, unsafe_allow_html=True)


def _render_retrospective(retrospective) -> None:
    if retrospective.intro:
        st.caption(retrospective.intro)

    if not retrospective.items:
        st.info("The latest retrospective contains no parseable stories.")
        return

    for item in retrospective.items:
        title = html.escape(item.title)
        link = _safe_url(item.link)
        if link:
            body = (
                f'<a href="{html.escape(link, quote=True)}" '
                f'target="_blank" rel="noopener">{title}</a>'
            )
        else:
            body = title
        dates = f"<br>{html.escape(item.dates)}" if item.dates else ""
        card = (
            '<div class="ann-retro-card">'
            f'<div class="ann-item"><span class="ann-rank">{item.rank:02d}</span>{body}</div>'
            f'<div class="ann-retro-meta">{html.escape(item.meta)}{dates}</div>'
            "</div>"
        )
        st.markdown(card, unsafe_allow_html=True)

    if retrospective.note:
        st.caption(retrospective.note)


def _digest_signature(repo_root: str) -> tuple[str, int] | None:
    state = find_latest_digest_state(repo_root)
    if state is None:
        return None
    return (os.path.basename(state.path), state.mtime_ns)


def _retrospective_signature(repo_root: str) -> tuple[str, int] | None:
    state = find_latest_retrospective_state(repo_root)
    if state is None:
        return None
    return (os.path.basename(state.path), state.mtime_ns)


def _content_signature(repo_root: str) -> tuple[tuple[str, int] | None, tuple[str, int] | None]:
    return (_digest_signature(repo_root), _retrospective_signature(repo_root))


@st.fragment(run_every=f"{REFRESH_POLL_SECONDS}s")
def _watch_latest_content(repo_root: str) -> None:
    current = _content_signature(repo_root)
    if st.session_state.get(CONTENT_STATE_KEY) == current:
        return
    st.session_state[CONTENT_STATE_KEY] = current
    st.rerun()


def main() -> None:
    latest = find_latest_digest(REPO_ROOT)
    latest_retrospective = find_latest_retrospective(REPO_ROOT)
    st.session_state[CONTENT_STATE_KEY] = _content_signature(REPO_ROOT)
    _watch_latest_content(REPO_ROOT)

    with st.sidebar:
        st.markdown('<div class="ann-kicker">All the news you need</div>', unsafe_allow_html=True)
        st.markdown("## ANN")
        st.caption("A tiny daily digest of what is likely to still matter in 30 days — not what is going viral today.")
        st.divider()
        if latest:
            st.markdown(f"**Digest:** `{os.path.basename(latest)}`")
        if latest_retrospective:
            st.markdown(f"**Retrospective:** `{os.path.basename(latest_retrospective)}`")
        if latest or latest_retrospective:
            st.caption(f"Auto-checking for updated files every {REFRESH_POLL_SECONDS} seconds.")
        if st.button("Refresh", use_container_width=True):
            st.rerun()
        st.divider()
        st.markdown('<div class="ann-kicker">Outlets</div>', unsafe_allow_html=True)
        for outlet, accent in OUTLET_ACCENTS.items():
            st.markdown(
                f'<div style="margin:6px 0;"><span class="ann-outlet-dot" '
                f'style="display:inline-block;width:10px;height:10px;border-radius:50%;'
                f'background:{accent};margin-right:8px;"></span>{outlet}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("# All the News You Need")

    daily_tab, retro_tab = st.tabs(["Daily digest", "Weekly retrospective"])

    with daily_tab:
        st.markdown('<div class="ann-kicker">Headline rotation · 10s each</div>', unsafe_allow_html=True)
        if not latest:
            st.warning("No digest found. Run `python ann.py run` to generate today's headlines.")
        else:
            with open(latest, encoding="utf-8") as f:
                sections = parse_digest(f.read())

            headlines = [
                {"outlet": h.outlet, "rank": h.rank, "title": h.title, "link": h.link}
                for h in flatten_headlines(sections)
            ]

            if headlines:
                components.html(_rotation_component(headlines, OUTLET_ACCENTS), height=320)
            else:
                st.info("The latest digest contains no parseable headlines.")

            st.markdown("### Full digest")
            _render_digest(sections)

    with retro_tab:
        st.markdown('<div class="ann-kicker">What still mattered</div>', unsafe_allow_html=True)
        if not latest_retrospective:
            st.warning("No retrospective found. Run `python ann.py retro` after at least two daily digests.")
        else:
            with open(latest_retrospective, encoding="utf-8") as f:
                retrospective = parse_retrospective(f.read())
            st.markdown(f"### {retrospective.title or os.path.basename(latest_retrospective)}")
            _render_retrospective(retrospective)


if __name__ == "__main__":
    main()
