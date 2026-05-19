"""
Scrape medical building developments from Berlin FIS-Broker (Geoportal).
FIS-Broker is Berlin's official geospatial data portal.
"""
import requests
import json
import time
from typing import Optional

# FIS-Broker API endpoints
FIS_BROKER_API = "https://fbinter.stadt-berlin.de/fb/wfs"

def search_berlin_developments() -> list[dict]:
    """
    Search FIS-Broker for medical/healthcare building development projects in Berlin.

    Note: This uses the WFS (Web Feature Service) API which requires specific
    layer knowledge. For MVP, we'll search available development/planning data.
    """
    projects = []

    # Common search keywords for healthcare buildings in German
    keywords = [
        "Ärztehaus",
        "Ärztezentrum",
        "Medizinisches Zentrum",
        "Praxiszentrum",
        "Gesundheitszentrum",
    ]

    try:
        # FIS-Broker exposes various layers. We look for building/development layers
        # This is a simplified approach - in production we'd use specific layer IDs

        # Try to fetch from development/construction layers
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetPropertyValue",
            "typeNames": "fis:beschreibung",  # Description layer
            "valueReference": "name",
        }

        response = requests.get(FIS_BROKER_API, params=params, timeout=10)
        response.raise_for_status()

        # Parse XML response (FIS returns GML/XML)
        # This is a basic parsing - real implementation would use lxml
        if response.text:
            # Search for healthcare keywords in response
            for keyword in keywords:
                if keyword.lower() in response.text.lower():
                    projects.append({
                        "name": f"FIS-Broker Development ({keyword})",
                        "city": "Berlin",
                        "source": "FIS-Broker Berlin",
                        "description": f"Medical building development in Berlin containing keyword: {keyword}",
                        "url": "https://fbinter.stadt-berlin.de/fb/",
                    })

    except requests.exceptions.RequestException as e:
        print(f"FIS-Broker API error: {e}")
        print("Note: FIS-Broker may require authentication or specific parameters")

    return projects


def search_berlin_council_decisions() -> list[dict]:
    """
    Search Berlin municipal council (BVV) decisions for building approvals.
    These are published on official council websites.
    """
    projects = []

    # This would integrate with Berlin district council (BVV) decision archives
    # For now, we document the approach

    print("Berlin council decisions: Not yet implemented (requires parser for each BVV)")
    # In production, we'd scrape:
    # https://www.berlin.de/ba-XXXX/org/wirtschaft/ (each district)
    # And search for building approval decisions (Baugenehmigungen)

    return projects


def get_berlin_projects() -> list[dict]:
    """Fetch all Berlin projects from available sources."""
    print("Searching Berlin geospatial data (FIS-Broker)...")
    fis_projects = search_berlin_developments()

    print(f"Found {len(fis_projects)} from FIS-Broker")

    return fis_projects
