import feedparser
import requests
from urllib.parse import quote
from datetime import datetime, timezone

SEEDS = [
    "latest company annual report business model revenue strategy",
    "recent central bank economic outlook inflation interest rates",
    "latest consumer spending retail industry business strategy",
    "recent technology company earnings business model analysis",
    "global economy financial literacy banking payments business",
    "recent corporate strategy supply chain manufacturing business",
    "government economic data household finance savings inflation",
]

HEADERS = {"User-Agent": "MoneyPilotAI/1.0 (topic research; educational channel)"}


def find_topic():
    candidates = {}
    for seed in SEEDS:
        url = "https://news.google.com/rss/search?q=" + quote(seed) + "&hl=en-US&gl=US&ceid=US:en"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as exc:
            print(f"Research feed unavailable for '{seed}': {exc}")
            continue
        for entry in feed.entries[:8]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not title or not link:
                continue
            key = title.lower()
            published = getattr(entry, "published_parsed", None)
            timestamp = 0
            if published:
                try:
                    timestamp = int(datetime(*published[:6], tzinfo=timezone.utc).timestamp())
                except Exception:
                    pass
            source = getattr(getattr(entry, "source", {}), "title", "") or ""
            existing = candidates.get(key)
            candidate = {"title": title, "url": link, "publisher": source,
                         "published_timestamp": timestamp, "discovery_query": seed}
            if existing is None or timestamp > existing["published_timestamp"]:
                candidates[key] = candidate

    if candidates:
        ranked = sorted(candidates.values(), key=lambda item: item["published_timestamp"], reverse=True)
        return ranked[0]

    return {
        "title": "How compound interest works: a practical money explainer",
        "url": "https://www.investor.gov/financial-tools-calculators/calculators/compound-interest-calculator",
        "publisher": "Investor.gov",
        "published_timestamp": 0,
        "discovery_query": "evergreen fallback",
    }
