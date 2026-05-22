"""
Google News RSS scraper — fetches real news articles about medical buildings
across our target cities. Free, no API key, no auth.

We hit Google News' RSS search endpoint for each (city × keyword) combination,
deduplicate by URL, and produce items in the same shape as the OParl scraper
so they flow through the existing qualification pipeline.

Why this is a "second different public source" (per the brief):
- OParl gives us district council motions (12-24mo lookahead, narrow but verifiable)
- Google News gives us press coverage of developer announcements
  (broader recall, includes Q2 2026 events, links back to original sources)
"""
from __future__ import annotations
import sys
import time
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote
import requests
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


# Search queries — combine each medical term with each target city.
# Google News RSS interprets the q= parameter the same as a regular search.
MEDICAL_QUERIES = [
    "Ärztehaus",
    "Medizinisches Versorgungszentrum",
    "Praxisklinik",
    "Gesundheitszentrum",
    "neues Ärztezentrum",
]

TARGET_CITIES = [
    "Berlin",
    "Potsdam",
    "Cottbus",
    "Magdeburg",
    "Halle",
    "Leipzig",
    "Dresden",
]


@dataclass
class NewsItem:
    """A single matched news article."""
    title: str
    link: str
    pub_date: Optional[str]
    source: str
    description: str
    city: str
    query: str

    def to_project_dict(self) -> dict:
        return {
            "name": self.title[:200],
            "city": self.city,
            "source": f"Google News ({self.source or 'Web'})",
            "description": self.description[:500] or self.title,
            "url": self.link,
            "_news_query": self.query,
            "_news_source": self.source,
            "_news_pub_date": self.pub_date,
        }


# ---------------------------------------------------------------------------
# HTTP fetch
# ---------------------------------------------------------------------------
def _fetch_rss(url: str, timeout: int = 10) -> Optional[str]:
    headers = {
        "User-Agent": "Aerztehaus-Radar/0.1 (+https://github.com/ERIC10000/ray-ai-physiotherapy--case-study)",
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"    ✗ Fetch failed: {type(e).__name__}: {e}")
        return None


# ---------------------------------------------------------------------------
# RSS parsing — Google News uses a slightly non-standard format
# ---------------------------------------------------------------------------
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return _HTML_TAG_RE.sub("", text).strip()


def _parse_google_news_rss(xml_text: str, city: str, query: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"    ✗ XML parse failed: {e}")
        return items

    # Google News RSS: <rss><channel><item>...</item></channel></rss>
    channel = root.find("channel")
    if channel is None:
        return items

    for item_el in channel.findall("item"):
        title = (item_el.findtext("title") or "").strip()
        link = (item_el.findtext("link") or "").strip()
        pub_date = (item_el.findtext("pubDate") or "").strip()
        # Description in Google News usually contains HTML with source attribution
        raw_desc = item_el.findtext("description") or ""
        description = _strip_html(raw_desc)
        # Source — Google News encodes it as <source>...</source>
        source_el = item_el.find("source")
        source_name = (source_el.text or "").strip() if source_el is not None else ""

        if not title or not link:
            continue

        items.append(NewsItem(
            title=title,
            link=link,
            pub_date=pub_date,
            source=source_name,
            description=description,
            city=city,
            query=query,
        ))
    return items


# ---------------------------------------------------------------------------
# Scraping driver
# ---------------------------------------------------------------------------
def scrape_news(
    cities: list[str] = TARGET_CITIES,
    queries: list[str] = MEDICAL_QUERIES,
    max_items_per_query: int = 10,
) -> list[dict]:
    """
    Run all (city × query) combinations, deduplicate by URL, return as project dicts.
    Google News doesn't accept a date range in RSS, but results are sorted by recency.
    """
    all_items: list[NewsItem] = []
    seen_links: set[str] = set()
    total_queries = len(cities) * len(queries)
    completed = 0

    print(f"Google News RSS — running {total_queries} (city × query) searches\n")

    for city in cities:
        for query in queries:
            completed += 1
            full_query = f"{query} {city}"
            url = (
                f"https://news.google.com/rss/search"
                f"?q={quote(full_query)}&hl=de&gl=DE&ceid=DE:de"
            )
            print(f"[{completed}/{total_queries}] {full_query}")
            xml_text = _fetch_rss(url)
            if not xml_text:
                continue
            items = _parse_google_news_rss(xml_text, city=city, query=query)[:max_items_per_query]
            added = 0
            for item in items:
                if item.link in seen_links:
                    continue
                seen_links.add(item.link)
                all_items.append(item)
                added += 1
            print(f"    {len(items)} item(s) returned, {added} new after dedup")
            # Polite delay — don't hammer Google
            time.sleep(0.3)

    print(f"\n{'='*60}")
    print(f"Total unique news items: {len(all_items)}")
    print(f"{'='*60}\n")
    return [i.to_project_dict() for i in all_items]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    import os

    results = scrape_news()
    if not results:
        print("No items found.")
        sys.exit(0)

    out_path = "output/news_matches.json"
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved {len(results)} match(es) to {out_path}")
    except Exception as e:
        print(f"Could not save: {e}")

    print(f"\nFirst 3 matches:\n")
    print(json.dumps(results[:3], indent=2, ensure_ascii=False))
