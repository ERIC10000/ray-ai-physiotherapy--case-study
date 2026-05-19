"""
Export qualified projects to CSV.
"""
import csv
import os
from qualification.schema import ProjectQualification

def export_to_csv(qualifications: list[ProjectQualification], filename: str = "output/leads.csv"):
    """Export qualified projects to CSV."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    if not qualifications:
        print("No qualifications to export")
        return

    with open(filename, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "Name",
            "City",
            "Source",
            "URL",
            "Description",
            "Is Healthcare Building",
            "Medical Office Building",
            "Physio Suitability (1-5)",
            "Estimated Stage",
            "Lead Quality",
            "Confidence (%)",
            "Reasoning",
            "Ground Floor",
            "Est. Size (sqm)",
            "Accessibility",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for qual in qualifications:
            writer.writerow(qual.to_dict())

    print(f"[OK] Exported {len(qualifications)} leads to {filename}")
