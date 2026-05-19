"""
Scrape medical building projects from press archives and news sources.
Uses Google News RSS and Bing News for comprehensive coverage.
"""
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time

TARGET_CITIES = {
    "Berlin": "Berlin",
    "Potsdam": "Potsdam",
    "Cottbus": "Cottbus",
    "Magdeburg": "Magdeburg",
    "Halle": "Halle",
    "Leipzig": "Leipzig",
    "Dresden": "Dresden",
}

HEALTHCARE_KEYWORDS = [
    "Ärztehaus",
    "Ärztezentrum",
    "Medizinisches Zentrum",
    "Praxiszentrum",
    "ambulatorisches Zentrum",
    "healthcare building",
    "medical office",
]

def search_google_news_rss() -> list[dict]:
    """
    Search Google News RSS feeds for healthcare building projects.
    """
    projects = []

    for city in TARGET_CITIES.keys():
        for keyword in HEALTHCARE_KEYWORDS[:3]:  # Limit to avoid rate limiting
            query = f"{keyword} {city}"
            rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=de&gl=DE&ceid=DE:de"

            try:
                print(f"  Fetching: {query}")
                feed = feedparser.parse(rss_url)

                if feed.entries:
                    for entry in feed.entries[:3]:  # Get top 3 per search
                        project = {
                            "name": entry.title[:80],
                            "city": city,
                            "source": "Google News",
                            "description": entry.summary[:200] if hasattr(entry, 'summary') else entry.title,
                            "url": entry.link if hasattr(entry, 'link') else "",
                        }
                        projects.append(project)

                time.sleep(0.5)  # Be respectful

            except Exception as e:
                print(f"  Error: {e}")
                continue

    return projects


def search_bing_news() -> list[dict]:
    """
    Search Bing News for medical building developments.
    """
    projects = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for city in TARGET_CITIES.keys():
        query = f"Ärztehaus {city} Neubau"
        search_url = f"https://www.bing.com/news/search?q={quote(query)}&setmkt=de-DE"

        try:
            print(f"  Searching Bing: {query}")
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            news_items = soup.find_all("div", {"class": "news-card"}, limit=3)

            for item in news_items:
                try:
                    title_elem = item.find("a", {"class": "title"})
                    desc_elem = item.find("p", {"class": "snippet"})

                    if title_elem:
                        project = {
                            "name": title_elem.get_text(strip=True)[:80],
                            "city": city,
                            "source": "Bing News",
                            "description": desc_elem.get_text(strip=True)[:200] if desc_elem else title_elem.get_text(strip=True),
                            "url": title_elem.get("href", ""),
                        }
                        projects.append(project)
                except Exception:
                    continue

            time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"  Bing search error: {e}")
            continue

    return projects


def search_developer_websites() -> list[dict]:
    """
    Search major German medical real estate developer websites.
    Examples: Gesundheit Projekte, Medical Properties, Ärztezentren Deutschland
    """
    projects = []

    # Common German healthcare property developers
    dev_sites = [
        {
            "name": "Gesundheit Projekte",
            "url": "https://www.gesundheit-projekte.de",
            "search_path": "/projekte"
        },
        {
            "name": "Medical Properties Germany",
            "url": "https://www.medical-properties.de",
            "search_path": "/portfolio"
        },
        {
            "name": "Ärztehaus Finder",
            "url": "https://www.aerztehaus-finder.de",
            "search_path": "/verfügbare-flächen"
        },
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for dev in dev_sites:
        try:
            print(f"  Checking: {dev['name']}")
            url = dev["url"] + dev["search_path"]
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for project listings
            project_links = soup.find_all("a", limit=5)
            for link in project_links:
                if any(kw.lower() in link.get_text().lower() for kw in HEALTHCARE_KEYWORDS):
                    project = {
                        "name": link.get_text(strip=True)[:80],
                        "city": "Multiple",
                        "source": f"Developer: {dev['name']}",
                        "description": link.get_text(strip=True),
                        "url": link.get("href", ""),
                    }
                    projects.append(project)

            time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"  Developer site error: {e}")
            continue

    return projects


def get_all_press_projects() -> list[dict]:
    """Fetch all projects from press and news sources."""
    print("\n[PRESS & NEWS SOURCES]")
    print("-" * 60)

    all_projects = []

    print("Google News RSS:")
    gn_projects = search_google_news_rss()
    all_projects.extend(gn_projects)
    print(f"  Found: {len(gn_projects)}")

    print("\nBing News:")
    bn_projects = search_bing_news()
    all_projects.extend(bn_projects)
    print(f"  Found: {len(bn_projects)}")

    print("\nDeveloper Websites:")
    dev_projects = search_developer_websites()
    all_projects.extend(dev_projects)
    print(f"  Found: {len(dev_projects)}")

    # Remove duplicates
    unique = []
    seen = set()
    for p in all_projects:
        key = (p["name"], p["city"])
        if key not in seen:
            unique.append(p)
            seen.add(key)

    print(f"\nTotal unique projects: {len(unique)}")
    return unique
