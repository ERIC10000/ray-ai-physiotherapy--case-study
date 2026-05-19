"""
LLM-based project qualifier using Claude API.
"""
import json
import os
from typing import Optional
from qualification.schema import ProjectQualification, QUALIFICATION_PROMPT

client = None

def _get_client():
    """Lazily initialize Anthropic client."""
    global client
    if client is None:
        from anthropic import Anthropic
        client = Anthropic()
    return client

def qualify_project(
    name: str,
    city: str,
    source: str,
    description: str,
    url: str
) -> Optional[ProjectQualification]:
    """
    Qualify a single project using Claude API.

    Returns ProjectQualification or None if parsing fails.
    """
    prompt = QUALIFICATION_PROMPT.format(
        name=name,
        city=city,
        source=source,
        description=description,
        url=url
    )

    try:
        client_instance = _get_client()
        message = client_instance.messages.create(
            model="claude-opus-4-7",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text

        # Extract JSON from response
        try:
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0]

            result = json.loads(json_str)
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Failed to parse JSON for {name}: {e}")
            print(f"Response: {response_text[:200]}")
            return None

        # Create ProjectQualification
        qualification = ProjectQualification(
            name=name,
            city=city,
            source=source,
            url=url,
            description=description,
            is_healthcare_building=result.get("is_healthcare_building", False),
            is_medical_office_building=result.get("is_medical_office_building", False),
            suitability_for_physio=result.get("suitability_for_physio", 1),
            estimated_stage=result.get("estimated_stage", "unknown"),
            lead_quality=result.get("lead_quality", "low"),
            confidence=result.get("confidence", 0),
            reasoning=result.get("reasoning", ""),
            ground_floor_available=result.get("ground_floor_available"),
            estimated_sqm=result.get("estimated_sqm"),
            accessibility_noted=result.get("accessibility_noted"),
        )

        return qualification

    except Exception as e:
        print(f"Error qualifying project {name}: {e}")
        return None

def batch_qualify_projects(projects: list[dict]) -> list[ProjectQualification]:
    """
    Qualify multiple projects.

    Each project dict should have: name, city, source, description, url
    """
    results = []
    for i, project in enumerate(projects):
        print(f"Qualifying {i+1}/{len(projects)}: {project['name'][:50]}")
        qualification = qualify_project(
            name=project["name"],
            city=project["city"],
            source=project["source"],
            description=project["description"],
            url=project["url"]
        )
        if qualification:
            results.append(qualification)

    return results
