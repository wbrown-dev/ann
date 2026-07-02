import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("ANN_MODEL", "claude-sonnet-5")

HEADLINES_PER_OUTLET = 5

# Each outlet maps to one or more RSS feeds. AP no longer publishes a public
# RSS feed, so it falls back to a Google News site-scoped query, which is the
# closest reliable substitute.
DEFAULT_OUTLET_FEEDS = {
    "WSJ": [
        "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
        "https://feeds.content.dowjones.io/public/rss/RSSUSnews",
        "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
        "https://feeds.content.dowjones.io/public/rss/RSSWSJD",
        "https://feeds.content.dowjones.io/public/rss/RSSOpinion",
    ],
    "NYT": [
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    ],
    "NBC": [
        "https://feeds.nbcnews.com/nbcnews/public/news",
        "https://feeds.nbcnews.com/nbcnews/public/world",
        "https://feeds.nbcnews.com/nbcnews/public/politics",
    ],
    "AP": [
        "https://news.google.com/rss/search?q=site:apnews.com+when:1d&hl=en-US&gl=US&ceid=US:en",
    ],
}

DEFAULT_OUTLET_DISPLAY_NAMES = {
    "WSJ": "WSJ",
    "NYT": "NYT",
    "NBC": "NBC",
    "AP": "AP",
}

DEFAULT_OUTLET_ACCENTS = {
    "WSJ": "#4dd0e1",
    "NYT": "#50a5ff",
    "NBC": "#7c4dff",
    "AP": "#c084fc",
}

# Optional outlets, off by default. Enable a comma-separated subset via
# ANN_EXTRA_OUTLETS (e.g. "GUARDIAN,BBC"). Each has a live, non-paywalled RSS
# feed that yields clean canonical article links (no Google News redirects).
EXTRA_OUTLET_FEEDS = {
    "GUARDIAN": [
        "https://www.theguardian.com/world/rss",
        "https://www.theguardian.com/us-news/rss",
        "https://www.theguardian.com/business/rss",
    ],
    "BBC": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
    "NPR": [
        "https://feeds.npr.org/1001/rss.xml",
        "https://feeds.npr.org/1004/rss.xml",
    ],
}

EXTRA_OUTLET_DISPLAY_NAMES = {
    "GUARDIAN": "The Guardian",
    "BBC": "BBC",
    "NPR": "NPR",
}

EXTRA_OUTLET_ACCENTS = {
    "GUARDIAN": "#ffb454",
    "BBC": "#ff6b81",
    "NPR": "#4ade80",
}


def _parse_extra_outlets(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [name.strip().upper() for name in raw.split(",") if name.strip()]


def resolve_outlet_config(
    extra_outlets_env: str | None,
) -> tuple[dict[str, list[str]], dict[str, str], dict[str, str]]:
    """Merge any enabled extra outlets onto the default four. Unknown names in
    ANN_EXTRA_OUTLETS are ignored so a typo cannot silently drop a real outlet."""
    feeds = {k: list(v) for k, v in DEFAULT_OUTLET_FEEDS.items()}
    display = dict(DEFAULT_OUTLET_DISPLAY_NAMES)
    accents = dict(DEFAULT_OUTLET_ACCENTS)

    seen: set[str] = set()
    for name in _parse_extra_outlets(extra_outlets_env):
        if name in EXTRA_OUTLET_FEEDS and name not in seen:
            seen.add(name)
            feeds[name] = list(EXTRA_OUTLET_FEEDS[name])
            display[name] = EXTRA_OUTLET_DISPLAY_NAMES[name]
            accents[name] = EXTRA_OUTLET_ACCENTS[name]

    return feeds, display, accents


OUTLET_FEEDS, OUTLET_DISPLAY_NAMES, OUTLET_ACCENTS = resolve_outlet_config(
    os.environ.get("ANN_EXTRA_OUTLETS")
)

SELECTION_STANDARD = """\
Headlines are selected based on significance, not virality; based on whether \
or not the story is likely to be significant in 30 days, not how many people \
are sharing it on social media.

Preference is given to developments with durable consequences, including:
- War and international conflict
- Law, courts, and constitutional questions
- Elections and governance
- Regulation and public policy
- Markets, trade, labor, and business
- Technology and scientific developments
- Public health, medical developments
- Infrastructure, energy, and logistics
- Major institutional changes

The digest intentionally avoids or deprioritizes:
- Celebrity news
- Crime-of-the-day stories
- Outrage bait
- Daily polling noise
- Social media controversies
- Partisan theater
- Viral curiosities
- Lifestyle filler
"""

REQUEST_TIMEOUT_SECONDS = 10
USER_AGENT = "Mozilla/5.0 (compatible; ANN-digest/1.0)"

# AP links arrive as opaque news.google.com redirect URLs. Resolving them to the
# canonical apnews.com article costs two extra requests per link, so it runs on
# selected headlines only. Kill switch in case Google changes the scheme again.
RESOLVE_GOOGLE_NEWS_URLS = os.environ.get("ANN_RESOLVE_URLS", "1").lower() not in (
    "0",
    "false",
    "no",
)
