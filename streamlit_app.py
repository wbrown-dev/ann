from __future__ import annotations

import json
import os
from datetime import datetime

import streamlit as st

from ann_app.config import OUTLET_ACCENTS
from ann_app.parse import (
    find_latest_digest,
    find_latest_digest_state,
    flatten_headlines,
    parse_digest,
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
    initial_sidebar_state="collapsed",
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

[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
footer {
  display: none !important;
}

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.block-container {
  padding: 0 !important;
  margin: 0 !important;
  max-width: none !important;
}

iframe {
  display: block;
  border: 0;
}

::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.7); }
::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #0ea5e9, #6366f1);
  border-radius: 8px;
}
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def _story_date_label(path: str | None) -> str:
    if not path:
        return "latest"
    stem = os.path.basename(path).removeprefix("headlines-").removesuffix(".md")
    try:
        return datetime.strptime(stem, "%Y-%m-%d").strftime("%b %-d, %Y")
    except ValueError:
        return stem


def _dashboard_component(
    headlines: list[dict],
    accents: dict[str, str],
    story_date: str,
) -> str:
    payload = json.dumps(headlines)
    accents_json = json.dumps(accents)
    outlets = json.dumps(list(accents))
    return f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

  :root {{
    --bg-1: #151a2b;
    --panel: rgba(22, 26, 46, 0.82);
    --panel-strong: rgba(13, 18, 34, 0.9);
    --border: rgba(132, 132, 168, 0.26);
    --text: #f5f7ff;
    --soft: rgba(245, 247, 255, 0.66);
    --cyan: #4dd0e1;
    --accent: {DEFAULT_ACCENT};
  }}

  * {{
    box-sizing: border-box;
  }}

  html,
  body {{
    width: 100%;
    min-height: 100%;
    margin: 0;
    background: #0f1426;
    color: var(--text);
    font-family: 'Manrope', 'Segoe UI', system-ui, sans-serif;
    overflow: hidden;
  }}

  body {{
    background:
      radial-gradient(circle at 20% 5%, rgba(124, 77, 255, 0.35), transparent 38%),
      radial-gradient(circle at 90% 20%, rgba(80, 165, 255, 0.26), transparent 35%),
      radial-gradient(circle at 60% 100%, rgba(192, 132, 252, 0.16), transparent 30%),
      linear-gradient(135deg, var(--bg-1), #0f1426 44%, #121833 100%);
  }}

  .grid-overlay {{
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
      linear-gradient(rgba(148, 163, 184, 0.055) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148, 163, 184, 0.055) 1px, transparent 1px);
    background-size: 36px 36px;
    mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 0.78), transparent 95%);
  }}

  .shell {{
    position: relative;
    width: 100vw;
    height: 100vh;
    min-height: 760px;
    display: grid;
    grid-template-rows: 112px minmax(0, 1fr);
  }}

  .topbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 72px 10px 38px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(18px);
  }}

  .brand {{
    display: flex;
    align-items: center;
    gap: 14px;
  }}

  .brand-mark {{
    width: 74px;
    height: 74px;
    border-radius: 14px;
    border: 1px solid rgba(165, 243, 252, 0.24);
    background: linear-gradient(135deg, #67e8f9 0%, #0ea5e9 54%, #1d4ed8 100%);
    box-shadow: 0 0 30px rgba(14, 165, 233, 0.45);
  }}

  .brand-title {{
    font-family: 'Space Grotesk', 'Manrope', sans-serif;
    font-size: 44px;
    line-height: 0.95;
    font-weight: 700;
    letter-spacing: 0.08em;
  }}

  .brand-line {{
    width: 330px;
    height: 2px;
    margin-top: 6px;
    background: rgba(77, 208, 225, 0.9);
    box-shadow: 0 0 10px rgba(34, 211, 238, 0.6);
  }}

  .brand-sub {{
    margin-top: 6px;
    color: rgba(224, 242, 254, 0.78);
    font-size: 12px;
    letter-spacing: 0.34em;
    text-transform: uppercase;
  }}

  .clock {{
    align-self: flex-end;
    padding-bottom: 10px;
    color: rgba(224, 242, 254, 0.82);
    font-family: 'JetBrains Mono', monospace;
    text-align: right;
    text-transform: uppercase;
    letter-spacing: 0.3em;
    font-size: 13px;
    line-height: 1.65;
  }}

  .body {{
    min-height: 0;
    display: grid;
    grid-template-columns: 260px minmax(0, 1fr);
    gap: 20px;
    padding: 20px 36px 36px;
  }}

  .rail {{
    min-height: 0;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.48);
    box-shadow: 0 22px 52px rgba(2, 6, 23, 0.38);
    backdrop-filter: blur(18px);
    padding: 14px;
    display: flex;
    flex-direction: column;
  }}

  .outlets {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}

  .outlet-button {{
    width: 100%;
    min-height: 52px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.055);
    color: rgba(245, 247, 255, 0.62);
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 0 16px;
    cursor: pointer;
    transition: 180ms ease;
  }}

  .outlet-button.is-active {{
    border-color: color-mix(in srgb, var(--active-color) 55%, transparent);
    background: linear-gradient(135deg, rgba(8, 47, 73, 0.48), rgba(14, 116, 144, 0.32));
    color: var(--text);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.22),
      0 8px 22px rgba(8, 145, 178, 0.25);
  }}

  .outlet-dot {{
    width: 11px;
    height: 11px;
    border-radius: 999px;
    background: var(--dot);
    box-shadow: 0 0 14px color-mix(in srgb, var(--dot) 70%, transparent);
  }}

  .outlet-name {{
    flex: 1;
    text-align: left;
  }}

  .active-pill {{
    min-width: 78px;
    height: 34px;
    align-self: flex-end;
    display: none;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: var(--active-color);
    color: #06111f;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
  }}

  .outlet-button.is-active .active-pill {{
    display: inline-flex;
  }}

  .slash-box {{
    width: 138px;
    height: 138px;
    margin: auto auto 2px;
    border: 1px solid rgba(77, 208, 225, 0.2);
    border-radius: 13px;
    background: rgba(2, 6, 23, 0.34);
    position: relative;
    overflow: hidden;
  }}

  .slash-box::before {{
    content: "";
    position: absolute;
    width: 20px;
    height: 102px;
    left: 58px;
    top: 20px;
    transform: skewX(-28deg) rotate(31deg);
    background: linear-gradient(180deg, #67e8f9, #06b6d4 48%, #1d4ed8);
    clip-path: polygon(50% 0, 100% 100%, 0 78%);
    filter: drop-shadow(0 0 12px rgba(34, 211, 238, 0.55));
  }}

  .main {{
    min-width: 0;
    min-height: 0;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.4);
    box-shadow: 0 22px 52px rgba(2, 6, 23, 0.38);
    backdrop-filter: blur(18px);
    padding: 46px 50px;
    display: flex;
    flex-direction: column;
    gap: 28px;
  }}

  .title-panel {{
    position: relative;
    border: 1px solid rgba(103, 232, 249, 0.18);
    border-radius: 18px;
    background: rgba(15, 23, 42, 0.52);
    padding: 26px 36px 24px;
    text-align: center;
    overflow: hidden;
  }}

  .main-title {{
    color: var(--cyan);
    font-family: 'Space Grotesk', 'Manrope', sans-serif;
    font-size: clamp(31px, 2.2vw, 42px);
    font-weight: 700;
    letter-spacing: 0.32em;
    text-transform: uppercase;
  }}

  .main-subtitle {{
    margin-top: 12px;
    color: rgba(245, 247, 255, 0.72);
    font-family: 'Space Grotesk', 'Manrope', sans-serif;
    font-size: clamp(13px, 1.1vw, 16px);
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }}

  .progress-track {{
    margin-top: 24px;
    height: 4px;
    width: 100%;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    overflow: hidden;
  }}

  .progress-fill {{
    height: 100%;
    width: 0;
    background: var(--accent);
    box-shadow: 0 0 12px var(--accent);
  }}

  .headline-panel {{
    flex: 1;
    min-height: 0;
    border: 1px solid rgba(103, 232, 249, 0.18);
    border-radius: 18px;
    background: rgba(13, 18, 34, 0.72);
    overflow: hidden;
    display: grid;
    grid-template-rows: minmax(0, 1fr) 82px;
  }}

  .headline-copy {{
    min-height: 0;
    padding: 54px 60px 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }}

  .headline-text {{
    margin: 0;
    color: #f8fbff !important;
    font-family: 'Space Grotesk', 'Manrope', sans-serif;
    font-size: clamp(30px, 3.7vw, 68px);
    line-height: 1.12;
    font-weight: 700;
    text-align: center;
    letter-spacing: 0;
    text-wrap: balance;
    transition: opacity 260ms ease, transform 260ms ease;
    text-shadow: 0 10px 34px rgba(0, 0, 0, 0.42);
  }}

  .headline-text.fade {{
    opacity: 0;
    transform: translateY(10px);
  }}

  .headline-footer {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
    padding: 0 34px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.035);
  }}

  .source-line {{
    min-width: 0;
    color: rgba(245, 247, 255, 0.62);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .counter {{
    color: rgba(245, 247, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    white-space: nowrap;
  }}

  .empty {{
    height: 100vh;
    display: grid;
    place-items: center;
    color: var(--text);
    font-size: 28px;
  }}

  @media (max-width: 900px) {{
    body {{
      overflow: auto;
    }}
    .shell {{
      min-height: 100vh;
      height: auto;
      grid-template-rows: auto auto;
    }}
    .topbar {{
      padding: 18px;
    }}
    .brand-mark {{
      width: 58px;
      height: 58px;
    }}
    .brand-title {{
      font-size: 34px;
    }}
    .brand-line {{
      width: 220px;
    }}
    .clock {{
      display: none;
    }}
    .body {{
      grid-template-columns: 1fr;
      padding: 16px;
    }}
    .rail {{
      min-height: auto;
    }}
    .outlets {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .slash-box {{
      display: none;
    }}
    .main {{
      padding: 20px;
    }}
    .headline-copy {{
      padding: 40px 24px;
    }}
    .headline-text {{
      font-size: clamp(30px, 10vw, 48px);
    }}
  }}
</style>
</head>
<body>
<div class="grid-overlay"></div>
<div class="shell">
  <header class="topbar">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true"></div>
      <div>
        <div class="brand-title">ANN</div>
        <div class="brand-line"></div>
        <div class="brand-sub">All the News You Need</div>
      </div>
    </div>
    <div class="clock">
      <div id="date-now">--</div>
      <div id="time-now">--:--</div>
    </div>
  </header>

  <div class="body">
    <aside class="rail">
      <nav class="outlets" id="outlets"></nav>
      <div class="slash-box" aria-hidden="true"></div>
    </aside>

    <main class="main">
      <section class="title-panel">
        <div class="main-title">Headline News</div>
        <div class="main-subtitle" id="story-meta">--</div>
        <div class="progress-track"><div class="progress-fill" id="progress"></div></div>
      </section>

      <section class="headline-panel">
        <div class="headline-copy">
          <h1 class="headline-text" id="headline">Loading headlines...</h1>
        </div>
        <div class="headline-footer">
          <div class="source-line" id="source"></div>
          <div class="counter" id="counter"></div>
        </div>
      </section>
    </main>
  </div>
</div>
<script>
(function() {{
  const items = {payload};
  const accents = {accents_json};
  const outlets = {outlets};
  const defaultAccent = "{DEFAULT_ACCENT}";
  const rotationMs = {ROTATION_SECONDS * 1000};
  const storyDate = {json.dumps(story_date)};

  const titleEl = document.getElementById('headline');
  const metaEl = document.getElementById('story-meta');
  const sourceEl = document.getElementById('source');
  const counterEl = document.getElementById('counter');
  const progressEl = document.getElementById('progress');
  const outletNav = document.getElementById('outlets');
  const dateNowEl = document.getElementById('date-now');
  const timeNowEl = document.getElementById('time-now');

  if (!items.length) {{
    document.body.innerHTML = '<div class="empty">No headlines available yet.</div>';
    return;
  }}

  function updateClock() {{
    const now = new Date();
    dateNowEl.textContent = now.toLocaleDateString('en-US', {{
      year: 'numeric',
      month: 'short',
      day: '2-digit'
    }});
    timeNowEl.textContent = now.toLocaleTimeString('en-US', {{
      hour: '2-digit',
      minute: '2-digit'
    }});
  }}

  function sourceText(item) {{
    if (!item.link) return 'cross-verified summary - no source link';
    return item.link.replace(/^https?:\\/\\//i, '');
  }}

  function buildOutletButtons() {{
    outlets.forEach((outlet) => {{
      const color = accents[outlet] || defaultAccent;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'outlet-button';
      button.dataset.outlet = outlet;
      button.style.setProperty('--dot', color);
      button.style.setProperty('--active-color', color);
      button.innerHTML = '<span class="outlet-dot"></span><span class="outlet-name">' +
        outlet + '</span><span class="active-pill">ON</span>';
      button.addEventListener('click', () => jumpToOutlet(outlet));
      outletNav.appendChild(button);
    }});
  }}

  function setActiveOutlet(outlet) {{
    document.querySelectorAll('.outlet-button').forEach((button) => {{
      button.classList.toggle('is-active', button.dataset.outlet === outlet);
    }});
  }}

  function fitHeadline() {{
    const box = titleEl.parentElement;
    if (!box) return;
    titleEl.style.fontSize = '';
    let size = parseFloat(getComputedStyle(titleEl).fontSize);
    while (
      size > 30 &&
      (titleEl.scrollHeight > box.clientHeight || titleEl.scrollWidth > box.clientWidth)
    ) {{
      size -= 2;
      titleEl.style.fontSize = size + 'px';
    }}
  }}

  let order = Array.from({{ length: items.length }}, (_, i) => i);
  let pos = 0;
  let elapsed = 0;
  let progressTimer = null;

  function render() {{
    const item = items[order[pos]];
    const accent = accents[item.outlet] || defaultAccent;
    document.documentElement.style.setProperty('--accent', accent);
    setActiveOutlet(item.outlet);

    titleEl.classList.add('fade');
    setTimeout(() => {{
      titleEl.textContent = item.title;
      metaEl.textContent = item.outlet.toLowerCase() + ' - ' + storyDate;
      sourceEl.textContent = sourceText(item);
      counterEl.textContent = String(pos + 1).padStart(2, '0') + ' / ' + items.length;
      fitHeadline();
      titleEl.classList.remove('fade');
    }}, 180);
  }}

  function advance() {{
    pos += 1;
    if (pos >= order.length) {{
      pos = 0;
    }}
    elapsed = 0;
    progressEl.style.width = '0%';
    render();
  }}

  function jumpToOutlet(outlet) {{
    const next = order.findIndex((idx) => items[idx].outlet === outlet);
    if (next >= 0) {{
      pos = next;
      elapsed = 0;
      progressEl.style.width = '0%';
      render();
    }}
  }}

  function startProgress() {{
    if (progressTimer) clearInterval(progressTimer);
    progressTimer = setInterval(() => {{
      elapsed += 200;
      progressEl.style.width = Math.min(100, (elapsed / rotationMs) * 100) + '%';
      if (elapsed >= rotationMs) advance();
    }}, 200);
  }}

  updateClock();
  setInterval(updateClock, 10000);
  buildOutletButtons();
  render();
  startProgress();
}})();
</script>
</body>
</html>
"""


def _digest_signature(repo_root: str) -> tuple[str, int] | None:
    state = find_latest_digest_state(repo_root)
    if state is None:
        return None
    return (os.path.basename(state.path), state.mtime_ns)


def _retrospective_signature(repo_root: str) -> tuple[str, int] | None:
    return None


def _content_signature(repo_root: str) -> tuple[str, int] | None:
    return _digest_signature(repo_root)


@st.fragment(run_every=f"{REFRESH_POLL_SECONDS}s")
def _watch_latest_content(repo_root: str) -> None:
    current = _content_signature(repo_root)
    if st.session_state.get(CONTENT_STATE_KEY) == current:
        return
    st.session_state[CONTENT_STATE_KEY] = current
    st.rerun()


def main() -> None:
    latest = find_latest_digest(REPO_ROOT)
    st.session_state[CONTENT_STATE_KEY] = _content_signature(REPO_ROOT)
    _watch_latest_content(REPO_ROOT)

    if not latest:
        st.warning("No digest found. Run `python ann.py run` to generate today's headlines.")
        return

    with open(latest, encoding="utf-8") as f:
        sections = parse_digest(f.read())

    headlines = [
        {"outlet": h.outlet, "rank": h.rank, "title": h.title, "link": _safe_url(h.link)}
        for h in flatten_headlines(sections)
    ]

    st.iframe(
        _dashboard_component(headlines, OUTLET_ACCENTS, _story_date_label(latest)),
        height=920,
    )


if __name__ == "__main__":
    main()
