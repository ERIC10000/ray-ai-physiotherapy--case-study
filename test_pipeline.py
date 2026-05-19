#!/usr/bin/env python3
"""
Test the qualification pipeline with mock data
"""
import os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not set")
    print("Set it with: export ANTHROPIC_API_KEY='your-key'")
    exit(1)

from qualification.llm_qualifier import qualify_project
from output.csv_exporter import export_to_csv

# Test projects - real examples based on German development news
test_projects = [
    {
        "name": "Ärztezentrum Leipzig Zentrum-Ost",
        "city": "Leipzig",
        "source": "Web Search",
        "description": "Neubau eines modernen Ärztezentrums mit ca. 350 qm auf der Ebene, 12 Ärzte, Erdgeschoss-Praxen, 2024 Fertigstellung",
        "url": "https://example.com/project1"
    },
    {
        "name": "Medical Office Berlin-Charlottenburg",
        "city": "Berlin",
        "source": "Google News",
        "description": "Planungen für neues Ärztezentrum in Charlottenburg, Bodenfläche ca. 400 qm, rollstuhlgerecht, Parkplätze für 20 Autos, Baubeginn Q2 2024",
        "url": "https://example.com/project2"
    },
    {
        "name": "Dresden Praxisklinik Neustädter Zentrum",
        "city": "Dresden",
        "source": "Web Search",
        "description": "Konzeptstudie für Praxisklinik Dresden, möglich 450 qm, mehrere Geschosse, zentrale Lage, noch in früher Planungsphase",
        "url": "https://example.com/project3"
    },
]

print("Testing LLM qualification pipeline...")
print("=" * 70)

qualifications = []
for i, project in enumerate(test_projects, 1):
    print(f"\n[{i}/{len(test_projects)}] Testing: {project['name']}")
    qual = qualify_project(
        name=project["name"],
        city=project["city"],
        source=project["source"],
        description=project["description"],
        url=project["url"]
    )
    if qual:
        print(f"✓ Result: {qual.lead_quality.upper()} lead (confidence: {qual.confidence}%)")
        qualifications.append(qual)
    else:
        print(f"✗ Failed to qualify")

print("\n" + "=" * 70)
print(f"Successfully qualified: {len(qualifications)}/{len(test_projects)}")

if qualifications:
    export_to_csv(qualifications, "output/test_leads.csv")
    print("\nSample results:")
    for qual in qualifications:
        print(f"  - {qual.name}: {qual.lead_quality} (suitability: {qual.suitability_for_physio}/5)")
