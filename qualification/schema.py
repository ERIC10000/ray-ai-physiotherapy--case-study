"""
Qualification schema for medical building projects.
"""
from dataclasses import dataclass
from typing import Literal

@dataclass
class ProjectQualification:
    """Structured qualification result from LLM."""
    name: str
    city: str
    source: str
    url: str
    description: str

    # Qualification fields
    is_healthcare_building: bool
    is_medical_office_building: bool
    suitability_for_physio: int  # 1-5 scale
    estimated_stage: Literal["concept", "planning", "approval", "construction", "marketing", "unknown"]
    lead_quality: Literal["high", "medium", "low"]
    confidence: int  # 0-100
    reasoning: str

    # Metadata
    ground_floor_available: bool | None
    estimated_sqm: int | None
    accessibility_noted: bool | None

    def to_dict(self):
        return {
            "Name": self.name,
            "City": self.city,
            "Source": self.source,
            "URL": self.url,
            "Description": self.description,
            "Is Healthcare Building": "Yes" if self.is_healthcare_building else "No",
            "Medical Office Building": "Yes" if self.is_medical_office_building else "No",
            "Physio Suitability (1-5)": self.suitability_for_physio,
            "Estimated Stage": self.estimated_stage,
            "Lead Quality": self.lead_quality,
            "Confidence (%)": self.confidence,
            "Reasoning": self.reasoning,
            "Ground Floor": "Yes" if self.ground_floor_available else ("No" if self.ground_floor_available is False else "Unknown"),
            "Est. Size (sqm)": self.estimated_sqm or "Unknown",
            "Accessibility": "Yes" if self.accessibility_noted else ("No" if self.accessibility_noted is False else "Unknown"),
        }

QUALIFICATION_PROMPT = """
You are an expert in real estate development and physiotherapy clinic site selection for meinphysio+ (Berlin, Germany).

Analyze this medical/healthcare building project and provide a structured qualification.

**Project Information:**
Name: {name}
City: {city}
Source: {source}
Description: {description}
URL: {url}

**Your Task:**
Qualify this project against these criteria:

1. **Is this a healthcare/medical building?** (not hospital, not residential, not generic commercial)
2. **Is it specifically a medical office building (Ärztehaus) or similar?**
3. **Suitability for physiotherapy** (1-5 scale):
   - Ground floor access (preferred)
   - Size: 250-450 sqm (ideal)
   - Accessibility (wheelchair, parking)
   - Location quality (pedestrian area, parking, public transit)
4. **Estimated development stage**: concept → planning → approval → construction → marketing
5. **Lead quality** (high/medium/low):
   - High: confirmed Ärztehaus, ground floor available, right size, early stage
   - Medium: likely healthcare building, some unknowns, decent stage
   - Low: unclear fit, late stage marketing, poor location or size
6. **Confidence in classification** (0-100%): How confident are you in this assessment?
7. **Reasoning**: Brief explanation of your scoring

**Respond in JSON format ONLY:**
{{
  "is_healthcare_building": boolean,
  "is_medical_office_building": boolean,
  "suitability_for_physio": 1-5,
  "estimated_stage": "concept|planning|approval|construction|marketing|unknown",
  "lead_quality": "high|medium|low",
  "confidence": 0-100,
  "reasoning": "string (1-2 sentences)",
  "ground_floor_available": true|false|null,
  "estimated_sqm": number|null,
  "accessibility_noted": true|false|null
}}
"""
