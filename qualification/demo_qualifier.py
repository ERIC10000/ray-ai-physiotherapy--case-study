"""
Demo qualifier - returns realistic mock results for testing pipeline.
Replace with real LLM qualifier when API key is available.
"""
import random
from qualification.schema import ProjectQualification

MOCK_RESPONSES = {
    "Ärztezentrum Leipzig Zentrum-Ost": {
        "is_healthcare_building": True,
        "is_medical_office_building": True,
        "suitability_for_physio": 5,
        "estimated_stage": "approval",
        "lead_quality": "high",
        "confidence": 95,
        "reasoning": "Confirmed Ärztehaus with 380sqm ground floor, excellent location, early stage.",
        "ground_floor_available": True,
        "estimated_sqm": 380,
        "accessibility_noted": True,
    },
    "Medizinisches Versorgungszentrum Berlin-Charlottenburg": {
        "is_healthcare_building": True,
        "is_medical_office_building": True,
        "suitability_for_physio": 4,
        "estimated_stage": "approval",
        "lead_quality": "high",
        "confidence": 92,
        "reasoning": "Medical supply center confirmed, 420sqm ground floor, excellent transit access.",
        "ground_floor_available": True,
        "estimated_sqm": 420,
        "accessibility_noted": True,
    },
    "Praxisklinik Dresden Altstadt-Zentrum": {
        "is_healthcare_building": True,
        "is_medical_office_building": True,
        "suitability_for_physio": 4,
        "estimated_stage": "concept",
        "lead_quality": "medium",
        "confidence": 85,
        "reasoning": "Practice clinic planned, right size (350-450sqm), early stage but high foot traffic.",
        "ground_floor_available": True,
        "estimated_sqm": 400,
        "accessibility_noted": None,
    },
    "Gesundheitszentrum Magdeburg-Südstadt": {
        "is_healthcare_building": True,
        "is_medical_office_building": False,
        "suitability_for_physio": 2,
        "estimated_stage": "planning",
        "lead_quality": "low",
        "confidence": 80,
        "reasoning": "Health center confirmed but not ground floor (1st floor), smaller size (280sqm), moderate location.",
        "ground_floor_available": False,
        "estimated_sqm": 280,
        "accessibility_noted": None,
    },
    "Ärztezentrum Potsdam Innenstadt": {
        "is_healthcare_building": True,
        "is_medical_office_building": True,
        "suitability_for_physio": 3,
        "estimated_stage": "approval",
        "lead_quality": "medium",
        "confidence": 88,
        "reasoning": "Ärztehaus confirmed, multi-level (not pure ground floor), good location, accessible.",
        "ground_floor_available": True,
        "estimated_sqm": 300,
        "accessibility_noted": True,
    },
    "Ambulantes Zentrum Cottbus Zentrum": {
        "is_healthcare_building": True,
        "is_medical_office_building": True,
        "suitability_for_physio": 4,
        "estimated_stage": "concept",
        "lead_quality": "medium",
        "confidence": 82,
        "reasoning": "Ambulatory center, 260sqm ground floor, excellent central location, early stage.",
        "ground_floor_available": True,
        "estimated_sqm": 260,
        "accessibility_noted": None,
    },
    "Arztpraxishaus Halle (Saale) Südpark": {
        "is_healthcare_building": True,
        "is_medical_office_building": True,
        "suitability_for_physio": 3,
        "estimated_stage": "planning",
        "lead_quality": "medium",
        "confidence": 80,
        "reasoning": "Medical practice house, 320sqm ground floor, peripheral location, Q2 2025 start.",
        "ground_floor_available": True,
        "estimated_sqm": 320,
        "accessibility_noted": None,
    },
    "Medizinische Versorgung Berlin-Friedrichshain": {
        "is_healthcare_building": True,
        "is_medical_office_building": False,
        "suitability_for_physio": 1,
        "estimated_stage": "construction",
        "lead_quality": "low",
        "confidence": 75,
        "reasoning": "Generic medical care facility, small space (200sqm mixed), advanced construction stage.",
        "ground_floor_available": None,
        "estimated_sqm": 200,
        "accessibility_noted": None,
    },
    "Ärztezentrum Leipzig-Gohlis Neubau": {
        "is_healthcare_building": True,
        "is_medical_office_building": True,
        "suitability_for_physio": 5,
        "estimated_stage": "marketing",
        "lead_quality": "high",
        "confidence": 98,
        "reasoning": "Confirmed Ärztehaus, 400sqm ground floor, prime location near park, marketing phase.",
        "ground_floor_available": True,
        "estimated_sqm": 400,
        "accessibility_noted": True,
    },
    "Gesundheitspark Dresden-Neustadt": {
        "is_healthcare_building": True,
        "is_medical_office_building": False,
        "suitability_for_physio": 2,
        "estimated_stage": "concept",
        "lead_quality": "low",
        "confidence": 70,
        "reasoning": "Health park (mixed use), medical portion 500+sqm multi-level, early stage, complex development.",
        "ground_floor_available": None,
        "estimated_sqm": 500,
        "accessibility_noted": None,
    },
}

def demo_qualify_project(
    name: str,
    city: str,
    source: str,
    description: str,
    url: str
) -> ProjectQualification:
    """
    Return mock qualification result for demo/testing.
    """
    # Try exact match first
    mock_result = MOCK_RESPONSES.get(name)

    if not mock_result:
        # Fall back to generic response based on keywords
        mock_result = {
            "is_healthcare_building": "Ärztehaus" in name or "medizin" in name.lower(),
            "is_medical_office_building": "Ärztehaus" in name,
            "suitability_for_physio": random.randint(2, 4),
            "estimated_stage": random.choice(["concept", "planning", "approval", "construction"]),
            "lead_quality": random.choice(["high", "medium", "low"]),
            "confidence": random.randint(70, 95),
            "reasoning": "Mock evaluation based on available information.",
            "ground_floor_available": None,
            "estimated_sqm": None,
            "accessibility_noted": None,
        }

    qualification = ProjectQualification(
        name=name,
        city=city,
        source=source,
        url=url,
        description=description,
        is_healthcare_building=mock_result["is_healthcare_building"],
        is_medical_office_building=mock_result["is_medical_office_building"],
        suitability_for_physio=mock_result["suitability_for_physio"],
        estimated_stage=mock_result["estimated_stage"],
        lead_quality=mock_result["lead_quality"],
        confidence=mock_result["confidence"],
        reasoning=mock_result["reasoning"],
        ground_floor_available=mock_result.get("ground_floor_available"),
        estimated_sqm=mock_result.get("estimated_sqm"),
        accessibility_noted=mock_result.get("accessibility_noted"),
    )

    return qualification


def batch_demo_qualify(projects: list[dict]) -> list[ProjectQualification]:
    """Qualify multiple projects with mock data."""
    results = []
    for i, project in enumerate(projects):
        print(f"Qualifying {i+1}/{len(projects)}: {project['name'][:50]}")
        qual = demo_qualify_project(
            name=project["name"],
            city=project["city"],
            source=project["source"],
            description=project["description"],
            url=project["url"]
        )
        results.append(qual)
    return results
