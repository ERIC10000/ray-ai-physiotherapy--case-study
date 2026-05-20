"""
Azure OpenAI-based project qualifier.
Mirrors llm_qualifier.py but uses Azure OpenAI (GPT-4o-mini etc.) instead of Anthropic.
"""
import json
import re
from typing import Optional
from qualification.schema import ProjectQualification, QUALIFICATION_PROMPT


def qualify_project_azure(
    name: str,
    city: str,
    source: str,
    description: str,
    url: str,
    *,
    endpoint: str,
    api_key: str,
    deployment: str,
    api_version: str = "2024-08-01-preview",
) -> tuple[Optional[ProjectQualification], dict]:
    """
    Qualify a single project using Azure OpenAI.

    Returns (qualification or None, meta dict with raw_response, latency_ms, error).
    """
    from openai import AzureOpenAI
    import time

    meta = {
        "provider": "azure-openai",
        "deployment": deployment,
        "raw_response": None,
        "latency_ms": None,
        "error": None,
    }

    prompt = QUALIFICATION_PROMPT.format(
        name=name,
        city=city,
        source=source,
        description=description,
        url=url,
    )

    try:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint.rstrip("/"),
        )

        t0 = time.time()
        response = client.chat.completions.create(
            model=deployment,  # In Azure this is the deployment name, not the model name
            messages=[
                {"role": "system", "content": "You are an expert in real estate qualification. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        meta["latency_ms"] = int((time.time() - t0) * 1000)

        response_text = response.choices[0].message.content or ""
        meta["raw_response"] = response_text
        meta["tokens_in"] = response.usage.prompt_tokens if response.usage else None
        meta["tokens_out"] = response.usage.completion_tokens if response.usage else None

        # Parse — Azure with response_format=json_object should return clean JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: strip code-fences if model wraps in them
            m = re.search(r"\{[\s\S]*\}", response_text)
            if not m:
                meta["error"] = "No JSON object found in response"
                return None, meta
            result = json.loads(m.group(0))

        qualification = ProjectQualification(
            name=name,
            city=city,
            source=source,
            url=url,
            description=description,
            is_healthcare_building=bool(result.get("is_healthcare_building", False)),
            is_medical_office_building=bool(result.get("is_medical_office_building", False)),
            suitability_for_physio=int(result.get("suitability_for_physio", 1)),
            estimated_stage=result.get("estimated_stage", "unknown"),
            lead_quality=result.get("lead_quality", "low"),
            confidence=int(result.get("confidence", 0)),
            reasoning=result.get("reasoning", ""),
            ground_floor_available=result.get("ground_floor_available"),
            estimated_sqm=result.get("estimated_sqm"),
            accessibility_noted=result.get("accessibility_noted"),
        )
        return qualification, meta

    except Exception as e:
        meta["error"] = f"{type(e).__name__}: {e}"
        return None, meta


def validate_azure_credentials(endpoint: str, api_key: str, deployment: str, api_version: str = "2024-08-01-preview") -> dict:
    """Make a tiny test call to verify credentials work. Returns {ok, error, latency_ms}."""
    from openai import AzureOpenAI
    import time

    try:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint.rstrip("/"),
        )
        t0 = time.time()
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        latency = int((time.time() - t0) * 1000)
        return {
            "ok": True,
            "latency_ms": latency,
            "model": deployment,
            "sample_response": (response.choices[0].message.content or "")[:30],
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
