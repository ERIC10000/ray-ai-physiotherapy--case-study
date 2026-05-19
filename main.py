#!/usr/bin/env python3
"""
Ärztehaus Radar: Main orchestrator
Discover and qualify medical building developments in target German cities
"""
import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from qualification.llm_qualifier import batch_qualify_projects
from output.csv_exporter import export_to_csv


def load_demo_data() -> list[dict]:
    """Load demo data for testing."""
    with open("demo_data.json", "r", encoding="utf-8") as f:
        return json.load(f)


def scrape_real_data() -> list[dict]:
    """Scrape real data from online sources."""
    from scrapers.press_archive_scraper import get_all_press_projects
    return get_all_press_projects()


def main():
    print("\n" + "=" * 70)
    print("ÄRZTEHAUS RADAR: AI-Native Medical Building Discovery")
    print("=" * 70)

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n[WARNING] ANTHROPIC_API_KEY not found")
        print("Using DEMO DATA mode (see demo_data.json)")
        print("\nTo use real scrapers:")
        print("  set ANTHROPIC_API_KEY=your-key")
        print("  python main.py --live")
        use_demo = True
    else:
        use_demo = "--demo" in sys.argv or not ("--live" in sys.argv)
        if use_demo:
            print("\nUsing DEMO DATA (realistic test projects)")
            print("To use real live scrapers: python main.py --live")

    # Step 1: Data Collection
    print("\n[STEP 1] LOADING DATA SOURCES")
    print("-" * 70)

    if use_demo:
        print("Loading demo data...")
        raw_projects = load_demo_data()
    else:
        print("Scraping real data sources...")
        raw_projects = scrape_real_data()

    if not raw_projects:
        print("ERROR: No projects found. Check your internet connection.")
        return

    print(f"Loaded {len(raw_projects)} projects")

    # Save raw data for reference
    os.makedirs("output", exist_ok=True)
    with open("output/raw_projects.json", "w", encoding="utf-8") as f:
        json.dump(raw_projects, f, indent=2, ensure_ascii=False)
    print(f"Raw data saved to output/raw_projects.json")

    # Step 2: LLM Qualification
    print("\n[STEP 2] QUALIFYING PROJECTS")
    print("-" * 70)

    if not api_key:
        print("Using DEMO QUALIFIER (mock results for testing)")
        from qualification.demo_qualifier import batch_demo_qualify
        qualifications = batch_demo_qualify(raw_projects)
    else:
        print("Using REAL LLM QUALIFIER (Claude API)")
        qualifications = batch_qualify_projects(raw_projects)

    if not qualifications:
        print("ERROR: No projects qualified. Check API key and responses.")
        return

    # Step 3: Output
    print("\n[STEP 3] EXPORTING RESULTS")
    print("-" * 70)
    export_to_csv(qualifications, "output/leads.csv")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Raw projects discovered: {len(raw_projects)}")
    print(f"Projects qualified: {len(qualifications)}")

    # High-quality leads
    high_quality = [q for q in qualifications if q.lead_quality == "high"]
    medium_quality = [q for q in qualifications if q.lead_quality == "medium"]
    low_quality = [q for q in qualifications if q.lead_quality == "low"]

    print(f"  - High quality: {len(high_quality)}")
    print(f"  - Medium quality: {len(medium_quality)}")
    print(f"  - Low quality: {len(low_quality)}")

    # Top leads
    print("\n[TOP LEADS]")
    print("-" * 70)
    for i, qual in enumerate(sorted(qualifications, key=lambda x: (x.lead_quality == "high", x.confidence), reverse=True)[:5], 1):
        print(f"{i}. {qual.name} ({qual.city})")
        print(f"   Quality: {qual.lead_quality.upper()} | Confidence: {qual.confidence}%")
        print(f"   Suitability: {qual.suitability_for_physio}/5 | Stage: {qual.estimated_stage}")
        print(f"   {qual.reasoning}")
        print()

    print("Full results in: output/leads.csv")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
