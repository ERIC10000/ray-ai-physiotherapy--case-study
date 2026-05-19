"""
Scrape medical building developments from Google News and web search.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time

TARGET_CITIES = {
    "Berlin": "Berlin",
    "Potsdam": "Potsdam, Brandenburg",
    "Cottbus": "Cottbus, Brandenburg",
    "Magdeburg": "Magdeburg, Sachsen-Anhalt",
    "Halle": "Halle (Saale), Sachsen-Anhalt",
    "Leipzig": "Leipzig, Sachsen",
    "Dresden": "Dresden, Sachsen",
}

SEARCH_QUERIES = [
    "Ärztehaus",
    "medical office building",
    "healthcare building",
    "Ärztezentrum",
    "medical center development",
    "ambulatory care center",
]

def search_google_news_for_projects(days_back: int = 180) -> list[dict]:
    """
    Search Google News for healthcare building projects in target cities.

    Returns list of projects with: name, city, source, description, url
    """
    projects = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for city, region in TARGET_CITIES.items():
        for query in SEARCH_QUERIES:
            search_term = f"{query} {city} Germany site:news.google.com"
            encoded_query = quote(search_term)
            url = f"https://news.google.com/search?q={encoded_query}"

            try:
                print(f"Searching: {query} in {city}")
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")

                # Google News uses dynamic loading, so we'll get limited results
                # This is a basic parsing - in production, we'd use Selenium
                articles = soup.find_all("article", limit=5)

                for article in articles:
                    try:
                        title_elem = article.find("h3")
                        link_elem = article.find("a", href=True)
                        source_elem = article.find("div", {"class": "VfPpkd-t08AT-Bz112c"})

                        if title_elem and link_elem:
                            project = {
                                "name": title_elem.get_text(strip=True)[:100],
                                "city": city,
                                "source": "Google News",
                                "description": title_elem.get_text(strip=True),
                                "url": link_elem.get("href", ""),
                            }
                            projects.append(project)
                    except Exception as e:
                        print(f"Error parsing article: {e}")
                        continue

            except requests.exceptions.RequestException as e:
                print(f"Error searching {city}: {e}")
                continue

            time.sleep(1)  # Be polite to servers

    return projects


def search_web_for_projects() -> list[dict]:
    """
    Search general web for healthcare building developments.
    Uses DuckDuckGo as a fallback (no API key needed).
    """
    projects = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for city, region in TARGET_CITIES.items():
        queries = [
            f"Ärztehaus {city} Neubau 2024 2025",
            f"Ärztezentrum {city} Entwicklung",
            f"medical office building {city} development",
        ]

        for query in queries:
            try:
                # Using DuckDuckGo HTML search (no API key)
                search_url = f"https://duckduckgo.com/html?q={quote(query)}"
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")
                results = soup.find_all("div", {"class": "result__body"}, limit=3)

                for result in results:
                    try:
                        title = result.find("a", {"class": "result__url"})
                        snippet = result.find("a", {"class": "result__snippet"})

                        if title:
                            project = {
                                "name": title.get_text(strip=True)[:100],
                                "city": city,
                                "source": "Web Search",
                                "description": snippet.get_text(strip=True) if snippet else title.get_text(strip=True),
                                "url": title.get("href", ""),
                            }
                            projects.append(project)
                    except Exception:
                        continue

            except requests.exceptions.RequestException as e:
                print(f"Error searching web for {city}: {e}")
                continue

            time.sleep(1)

    return projects


def get_all_projects() -> list[dict]:
    """Fetch projects from all sources."""
    print("=" * 60)
    print("DATA COLLECTION: Google News & Web Search")
    print("=" * 60)

    all_projects = []

    print("\n[1/2] Searching Google News...")
    news_projects = search_google_news_for_projects()
    all_projects.extend(news_projects)
    print(f"Found {len(news_projects)} from Google News")

    print("\n[2/2] Searching Web...")
    web_projects = search_web_for_projects()
    all_projects.extend(web_projects)
    print(f"Found {len(web_projects)} from Web Search")

    # Remove duplicates
    unique_projects = []
    seen_names = set()
    for p in all_projects:
        if p["name"] not in seen_names:
            unique_projects.append(p)
            seen_names.add(p["name"])

    print(f"\nTotal unique projects: {len(unique_projects)}")
    return unique_projects
