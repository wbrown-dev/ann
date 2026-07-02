import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("ANN_MODEL", "claude-sonnet-5")

HEADLINES_PER_OUTLET = 5

# Each outlet maps to one or more RSS feeds. AP no longer publishes a public
# RSS feed, so it falls back to a Google News site-scoped query, which is the
# closest reliable substitute.
OUTLET_FEEDS = {
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

OUTLET_DISPLAY_NAMES = {
    "WSJ": "WSJ",
    "NYT": "NYT",
    "NBC": "NBC",
    "AP": "AP",
}

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
