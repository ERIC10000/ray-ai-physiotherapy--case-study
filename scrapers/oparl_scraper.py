"""
OParl scraper — queries Berlin district council information systems (BVV)
for papers (Drucksachen) mentioning medical-building keywords.

This is REAL public data, not mocked. OParl is a standardized JSON REST API
(https://oparl.org) implemented by all Berlin districts via the ALLRIS platform.

Each district publishes:
- system endpoint  → list of bodies
- bodies endpoint  → BVV + committees
- papers endpoint  → individual motions/Drucksachen with title + PDF link
- meetings endpoint → meeting agendas + protocols

Why this matters: district councils discuss construction projects 12-24 months
before they hit public marketing. We catch them before competitors do.
"""
from __future__ import annotations
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Iterator, Optional
from datetime import datetime, timezone, timedelta
import requests

# Windows consoles default to cp1252 which can't encode arrows/check marks.
# Force UTF-8 so the printable output looks the same as on Linux/macOS.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


# ---------------------------------------------------------------------------
# Districts — verified BVV Mitte; the others follow the same ALLRIS / OParl
# pattern. Endpoints are confirmed by hitting /system.asp.
# ---------------------------------------------------------------------------
OPARL_DISTRICTS: dict[str, str] = {
    "Mitte":                       "https://www.sitzungsdienst-mitte.de/oi/oparl/1.0",
    "Friedrichshain-Kreuzberg":    "https://www.sitzungsdienst.fk.berlin.de/oi/oparl/1.0",
    "Pankow":                      "https://www.sitzungsdienst-pankow.de/oi/oparl/1.0",
    "Charlottenburg-Wilmersdorf":  "https://www.sitzungsdienst-cw.de/oi/oparl/1.0",
    "Spandau":                     "https://www.sitzungsdienst-spandau.de/oi/oparl/1.0",
    "Steglitz-Zehlendorf":         "https://www.sitzungsdienst-sz.de/oi/oparl/1.0",
    "Tempelhof-Schöneberg":        "https://www.sitzungsdienst-ts.de/oi/oparl/1.0",
    "Neukölln":                    "https://www.sitzungsdienst-neukoelln.de/oi/oparl/1.0",
    "Treptow-Köpenick":            "https://www.sitzungsdienst-tk.de/oi/oparl/1.0",
    "Marzahn-Hellersdorf":         "https://www.sitzungsdienst-mh.de/oi/oparl/1.0",
    "Lichtenberg":                 "https://www.sitzungsdienst-lichtenberg.de/oi/oparl/1.0",
    "Reinickendorf":               "https://www.sitzungsdienst-reinickendorf.de/oi/oparl/1.0",
}


# Medical-building keywords — match in paper titles/subjects.
# German real-estate terms used by district councils + senate planning.
MEDICAL_KEYWORDS = [
    "Ärztehaus", "ärztehaus",
    "Medizinisches Versorgungszentrum", "MVZ ", "MVZ-",
    "Praxisklinik", "Gesundheitszentrum",
    "Facharztzentrum", "Ambulantes Zentrum",
    "Tagesklinik", "Polyklinik",
    "Praxiszentrum",
    # broader — useful in motions about land-use changes
    "medizinische Versorgung", "Gesundheitsversorgung",
    "Arztpraxis", "Hausarzt",
]

# Construction/planning context — co-occurrence boosts relevance
CONSTRUCTION_KEYWORDS = [
    "Neubau", "Bauvorhaben", "Bebauungsplan", "Bauantrag",
    "Aufstellung", "Errichtung", "Sondergebiet", "Umnutzung",
]


@dataclass
class OparlPaper:
    """A single matched paper from an OParl endpoint."""
    district: str
    paper_id: str
    title: str
    reference: str
    paper_type: str
    created: Optional[str]
    modified: Optional[str]
    web_link: Optional[str]
    pdf_url: Optional[str]
    matched_keywords: list[str] = field(default_factory=list)

    def to_project_dict(self) -> dict:
        """Convert to the dict shape expected by the qualification pipeline."""
        return {
            "name": self.title[:200],
            "city": f"Berlin-{self.district}",
            "source": f"BVV {self.district} (OParl)",
            "description": (
                f"BVV-Drucksache {self.reference} ({self.paper_type}). "
                f"Erkannte Stichwörter: {', '.join(self.matched_keywords)}. "
                f"Volltext im PDF verfügbar."
            ),
            "url": self.web_link or self.pdf_url or "",
            "_oparl_paper_id": self.paper_id,
            "_oparl_district": self.district,
            "_pdf_url": self.pdf_url,
        }


# ---------------------------------------------------------------------------
# HTTP — small wrapper with timeout, retry, and a polite UA
# ---------------------------------------------------------------------------
def _http_get_json(url: str, timeout: int = 15, retries: int = 2) -> Optional[dict]:
    headers = {
        "User-Agent": "Aerztehaus-Radar/0.1 (case study; +https://github.com/ERIC10000/ray-ai-physiotherapy--case-study)",
        "Accept": "application/json",
    }
    last_err = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
    print(f"  ✗ GET {url}\n    {type(last_err).__name__}: {last_err}")
    return None


def _matches_keywords(text: str, keywords: list[str]) -> list[str]:
    """Case-insensitive substring match; returns the list of matched keywords."""
    if not text:
        return []
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


# ---------------------------------------------------------------------------
# OParl traversal
# ---------------------------------------------------------------------------
def _iter_papers(base_url: str, since: datetime, max_pages: int = 20) -> Iterator[dict]:
    """
    Iterate papers for a district's body, filtered by modified_since.
    Pages until exhausted or max_pages reached. Yields raw OParl paper objects.
    """
    iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{base_url}/papers.asp?body=1&modified_since={iso}"
    page = 0
    seen = 0
    while url and page < max_pages:
        page += 1
        data = _http_get_json(url)
        if not data:
            return
        for item in data.get("data", []):
            seen += 1
            yield item
        url = (data.get("links") or {}).get("next")
    print(f"    Fetched {seen} papers across {page} page(s)")


def scrape_district(
    district: str,
    base_url: str,
    since: datetime,
    keywords: list[str] = MEDICAL_KEYWORDS,
    max_pages: int = 20,
) -> list[OparlPaper]:
    """Scrape one district's papers, filter by keyword."""
    print(f"\n→ {district}")
    print(f"  Base: {base_url}")
    matches: list[OparlPaper] = []
    for paper in _iter_papers(base_url, since, max_pages=max_pages):
        title = paper.get("name") or ""
        subject = paper.get("subject") or ""
        haystack = f"{title}\n{subject}"
        hits = _matches_keywords(haystack, keywords)
        if not hits:
            continue
        main_file = paper.get("mainFile") or {}
        matches.append(OparlPaper(
            district=district,
            paper_id=paper.get("id", ""),
            title=title or subject or "(no title)",
            reference=paper.get("reference") or "",
            paper_type=paper.get("paperType") or "",
            created=paper.get("created"),
            modified=paper.get("modified"),
            web_link=paper.get("web"),
            pdf_url=main_file.get("downloadUrl") or main_file.get("accessUrl"),
            matched_keywords=hits,
        ))
        print(f"  ✓ Match: {title[:80]}  ({', '.join(hits)})")
    print(f"  → {len(matches)} match(es) in {district}")
    return matches


def scrape_all_districts(
    since_days: int = 365,
    districts: Optional[dict[str, str]] = None,
    keywords: list[str] = MEDICAL_KEYWORDS,
) -> list[dict]:
    """
    Top-level: scrape all configured districts, return projects in the
    qualification-pipeline dict format (compatible with main.py).
    """
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    districts = districts or OPARL_DISTRICTS

    all_matches: list[OparlPaper] = []
    reachable = 0
    failed = 0
    for district, base_url in districts.items():
        try:
            # Verify the endpoint is reachable before paginating
            system = _http_get_json(f"{base_url}/system.asp", timeout=8, retries=0)
            if not system:
                print(f"\n→ {district}: endpoint not reachable, skipping")
                failed += 1
                continue
            reachable += 1
            matches = scrape_district(district, base_url, since, keywords)
            all_matches.extend(matches)
        except Exception as e:
            print(f"  ✗ {district}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Reachable districts: {reachable}/{len(districts)}  (failed: {failed})")
    print(f"Total medical-keyword matches: {len(all_matches)}")
    print(f"{'='*60}")
    return [m.to_project_dict() for m in all_matches]


# ---------------------------------------------------------------------------
# CLI / standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    import sys

    days = int(sys.argv[1]) if len(sys.argv) > 1 else 365
    print(f"Scraping Berlin OParl endpoints for papers modified in last {days} days...")
    print(f"Keywords: {', '.join(MEDICAL_KEYWORDS[:6])} ...")
    results = scrape_all_districts(since_days=days)

    if results:
        print(f"\nFirst 3 matches as JSON:\n")
        print(json.dumps(results[:3], indent=2, ensure_ascii=False))

        out_path = "output/oparl_matches.json"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Saved {len(results)} match(es) to {out_path}")
        except Exception as e:
            print(f"Could not save: {e}")
    else:
        print("\nNo matches found. Try a wider time window: python oparl_scraper.py 730")
