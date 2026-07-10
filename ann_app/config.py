import os

from dotenv import load_dotenv

load_dotenv()


def _env_value(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


MODEL_PROVIDER = (_env_value("ANN_MODEL_PROVIDER") or "anthropic").lower()
DEFAULT_MODEL_BY_PROVIDER = {
    "anthropic": "claude-sonnet-5",
    "openai": "gpt-4.1-mini",
    "gemini": "gemini-2.5-flash",
}
MODEL_NAME = _env_value("ANN_MODEL") or DEFAULT_MODEL_BY_PROVIDER.get(
    MODEL_PROVIDER,
    DEFAULT_MODEL_BY_PROVIDER["anthropic"],
)
SUPPORTED_MODEL_PROVIDERS = tuple(DEFAULT_MODEL_BY_PROVIDER)

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


def resolve_model_settings(provider: str | None = None, model: str | None = None) -> tuple[str, str]:
    resolved_provider = ((provider.strip() if provider else None) or _env_value("ANN_MODEL_PROVIDER") or "anthropic").lower()
    if resolved_provider not in DEFAULT_MODEL_BY_PROVIDER:
        supported = ", ".join(SUPPORTED_MODEL_PROVIDERS)
        raise ValueError(f"unsupported model provider {resolved_provider!r}; choose one of: {supported}")

    resolved_model = (model.strip() if model else None) or _env_value("ANN_MODEL") or DEFAULT_MODEL_BY_PROVIDER[resolved_provider]

    return resolved_provider, resolved_model

REQUEST_TIMEOUT_SECONDS = 10
USER_AGENT = "Mozilla/5.0 (compatible; ANN-digest/1.0)"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_digest_dir(raw: str | None, repo_root: str = _REPO_ROOT) -> str:
    """Directory holding generated headlines-*.md / retrospective-*.md files.

    Defaults to the repo root so local use is unchanged. Containers point
    ANN_DIGEST_DIR at a mounted volume, which keeps the image immutable and
    read-only instead of bind-mounting the source tree over /app.
    """
    if not raw or not raw.strip():
        return repo_root
    return os.path.abspath(os.path.expanduser(raw.strip()))


DIGEST_DIR = resolve_digest_dir(os.environ.get("ANN_DIGEST_DIR"))

# AP links arrive as opaque news.google.com redirect URLs. Resolving them to the
# canonical apnews.com article costs two extra requests per link, so it runs on
# selected headlines only. Kill switch in case Google changes the scheme again.
RESOLVE_GOOGLE_NEWS_URLS = os.environ.get("ANN_RESOLVE_URLS", "1").lower() not in (
    "0",
    "false",
    "no",
)
