"""
Multi-provider LLM qualifier — supports Azure OpenAI, Anthropic Claude, Google Gemini, and OpenAI.

Each provider exposes two functions via the unified dispatchers at the bottom:
- validate(provider, credentials) -> {ok, latency_ms, model, sample_response, error}
- qualify(provider, credentials, project) -> (qualification_dict | None, meta_dict)
"""
import json
import re
import time


QUALIFICATION_PROMPT = """You are an expert in real estate development and physiotherapy clinic site selection.

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
3. **Suitability for physiotherapy** (1-5 scale): ground floor, size 250-450 sqm, accessibility, location quality
4. **Estimated development stage**: concept / planning / approval / construction / marketing
5. **Lead quality** (high/medium/low)
6. **Confidence** (0-100%)
7. **Reasoning** (1-2 sentences)

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
}}"""


def _parse_json_response(text):
    """Parse JSON from an LLM response — handles plain JSON, fenced JSON, and embedded JSON."""
    text = (text or '').strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip ```json ... ``` fences
    if '```' in text:
        m = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
        if m:
            return json.loads(m.group(1))
    # Find first JSON object anywhere
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        return json.loads(m.group(0))
    raise ValueError('No JSON object found in response')


def _to_qualification_dict(name, city, source, url, description, parsed):
    """Convert parsed JSON into the dashboard's expected lead shape."""
    gf = parsed.get('ground_floor_available')
    acc = parsed.get('accessibility_noted')
    return {
        'Name': name,
        'City': city,
        'Source': source,
        'URL': url,
        'Description': description,
        'Is Healthcare Building': 'Yes' if parsed.get('is_healthcare_building') else 'No',
        'Medical Office Building': 'Yes' if parsed.get('is_medical_office_building') else 'No',
        'Physio Suitability (1-5)': int(parsed.get('suitability_for_physio', 1)),
        'Estimated Stage': parsed.get('estimated_stage', 'unknown'),
        'Lead Quality': parsed.get('lead_quality', 'low'),
        'Confidence (%)': int(parsed.get('confidence', 0)),
        'Reasoning': parsed.get('reasoning', ''),
        'Ground Floor': 'Yes' if gf else ('No' if gf is False else 'Unknown'),
        'Est. Size (sqm)': parsed.get('estimated_sqm') or 'Unknown',
        'Accessibility': 'Yes' if acc else ('No' if acc is False else 'Unknown'),
    }


# ========================================================================
# AZURE OPENAI
# ========================================================================

def _azure_client(creds):
    from openai import AzureOpenAI
    return AzureOpenAI(
        api_key=creds['api_key'],
        api_version=creds.get('api_version', '2024-08-01-preview'),
        azure_endpoint=creds['endpoint'].rstrip('/'),
    )


def validate_azure(creds):
    try:
        client = _azure_client(creds)
        t0 = time.time()
        response = client.chat.completions.create(
            model=creds['deployment'],
            messages=[{'role': 'user', 'content': 'ping'}],
            max_tokens=5,
        )
        return {
            'ok': True,
            'latency_ms': int((time.time() - t0) * 1000),
            'model': creds['deployment'],
            'sample_response': (response.choices[0].message.content or '')[:30],
        }
    except Exception as e:
        return {'ok': False, 'error': f'{type(e).__name__}: {e}'}


def qualify_azure(creds, project):
    meta = {'provider': 'azure-openai', 'model': creds.get('deployment'), 'latency_ms': None, 'error': None}
    try:
        client = _azure_client(creds)
        prompt = QUALIFICATION_PROMPT.format(**project)
        t0 = time.time()
        response = client.chat.completions.create(
            model=creds['deployment'],
            messages=[
                {'role': 'system', 'content': 'You are an expert in real estate qualification. Respond with valid JSON only.'},
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.2,
            max_tokens=600,
            response_format={'type': 'json_object'},
        )
        meta['latency_ms'] = int((time.time() - t0) * 1000)
        text = response.choices[0].message.content or ''
        meta['raw_response'] = text
        if response.usage:
            meta['tokens_in'] = response.usage.prompt_tokens
            meta['tokens_out'] = response.usage.completion_tokens
        parsed = _parse_json_response(text)
        return _to_qualification_dict(project['name'], project['city'], project['source'], project['url'], project['description'], parsed), meta
    except Exception as e:
        meta['error'] = f'{type(e).__name__}: {e}'
        return None, meta


# ========================================================================
# ANTHROPIC CLAUDE
# ========================================================================

DEFAULT_ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'


def validate_anthropic(creds):
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=creds['api_key'])
        model = creds.get('model') or DEFAULT_ANTHROPIC_MODEL
        t0 = time.time()
        response = client.messages.create(
            model=model,
            max_tokens=5,
            messages=[{'role': 'user', 'content': 'ping'}],
        )
        return {
            'ok': True,
            'latency_ms': int((time.time() - t0) * 1000),
            'model': model,
            'sample_response': (response.content[0].text if response.content else '')[:30],
        }
    except Exception as e:
        return {'ok': False, 'error': f'{type(e).__name__}: {e}'}


def qualify_anthropic(creds, project):
    model = creds.get('model') or DEFAULT_ANTHROPIC_MODEL
    meta = {'provider': 'anthropic', 'model': model, 'latency_ms': None, 'error': None}
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=creds['api_key'])
        prompt = QUALIFICATION_PROMPT.format(**project)
        t0 = time.time()
        response = client.messages.create(
            model=model,
            max_tokens=600,
            messages=[{'role': 'user', 'content': prompt + '\n\nRespond with valid JSON only, no preamble.'}],
        )
        meta['latency_ms'] = int((time.time() - t0) * 1000)
        text = response.content[0].text if response.content else ''
        meta['raw_response'] = text
        if hasattr(response, 'usage') and response.usage:
            meta['tokens_in'] = response.usage.input_tokens
            meta['tokens_out'] = response.usage.output_tokens
        parsed = _parse_json_response(text)
        return _to_qualification_dict(project['name'], project['city'], project['source'], project['url'], project['description'], parsed), meta
    except Exception as e:
        meta['error'] = f'{type(e).__name__}: {e}'
        return None, meta


# ========================================================================
# GOOGLE GEMINI
# ========================================================================

DEFAULT_GEMINI_MODEL = 'gemini-1.5-flash'


def validate_gemini(creds):
    try:
        import google.generativeai as genai
        genai.configure(api_key=creds['api_key'])
        model_name = creds.get('model') or DEFAULT_GEMINI_MODEL
        model = genai.GenerativeModel(model_name)
        t0 = time.time()
        response = model.generate_content('ping', generation_config={'max_output_tokens': 5})
        return {
            'ok': True,
            'latency_ms': int((time.time() - t0) * 1000),
            'model': model_name,
            'sample_response': (response.text or '')[:30],
        }
    except Exception as e:
        return {'ok': False, 'error': f'{type(e).__name__}: {e}'}


def qualify_gemini(creds, project):
    model_name = creds.get('model') or DEFAULT_GEMINI_MODEL
    meta = {'provider': 'google-gemini', 'model': model_name, 'latency_ms': None, 'error': None}
    try:
        import google.generativeai as genai
        genai.configure(api_key=creds['api_key'])
        model = genai.GenerativeModel(
            model_name,
            generation_config={
                'temperature': 0.2,
                'max_output_tokens': 600,
                'response_mime_type': 'application/json',
            },
        )
        prompt = QUALIFICATION_PROMPT.format(**project)
        t0 = time.time()
        response = model.generate_content(prompt)
        meta['latency_ms'] = int((time.time() - t0) * 1000)
        text = response.text or ''
        meta['raw_response'] = text
        # Gemini usage metadata if available
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            meta['tokens_in'] = response.usage_metadata.prompt_token_count
            meta['tokens_out'] = response.usage_metadata.candidates_token_count
        parsed = _parse_json_response(text)
        return _to_qualification_dict(project['name'], project['city'], project['source'], project['url'], project['description'], parsed), meta
    except Exception as e:
        meta['error'] = f'{type(e).__name__}: {e}'
        return None, meta


# ========================================================================
# OPENAI (direct, not Azure)
# ========================================================================

DEFAULT_OPENAI_MODEL = 'gpt-4o-mini'


def _openai_client(creds):
    from openai import OpenAI
    kwargs = {'api_key': creds['api_key']}
    if creds.get('org_id'):
        kwargs['organization'] = creds['org_id']
    return OpenAI(**kwargs)


def validate_openai(creds):
    try:
        client = _openai_client(creds)
        model = creds.get('model') or DEFAULT_OPENAI_MODEL
        t0 = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'ping'}],
            max_tokens=5,
        )
        return {
            'ok': True,
            'latency_ms': int((time.time() - t0) * 1000),
            'model': model,
            'sample_response': (response.choices[0].message.content or '')[:30],
        }
    except Exception as e:
        return {'ok': False, 'error': f'{type(e).__name__}: {e}'}


def qualify_openai(creds, project):
    model = creds.get('model') or DEFAULT_OPENAI_MODEL
    meta = {'provider': 'openai', 'model': model, 'latency_ms': None, 'error': None}
    try:
        client = _openai_client(creds)
        prompt = QUALIFICATION_PROMPT.format(**project)
        t0 = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': 'You are an expert in real estate qualification. Respond with valid JSON only.'},
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.2,
            max_tokens=600,
            response_format={'type': 'json_object'},
        )
        meta['latency_ms'] = int((time.time() - t0) * 1000)
        text = response.choices[0].message.content or ''
        meta['raw_response'] = text
        if response.usage:
            meta['tokens_in'] = response.usage.prompt_tokens
            meta['tokens_out'] = response.usage.completion_tokens
        parsed = _parse_json_response(text)
        return _to_qualification_dict(project['name'], project['city'], project['source'], project['url'], project['description'], parsed), meta
    except Exception as e:
        meta['error'] = f'{type(e).__name__}: {e}'
        return None, meta


# ========================================================================
# UNIFIED DISPATCHERS
# ========================================================================

PROVIDERS = {
    'azure': {'validate': validate_azure, 'qualify': qualify_azure, 'required': ['endpoint', 'api_key', 'deployment']},
    'anthropic': {'validate': validate_anthropic, 'qualify': qualify_anthropic, 'required': ['api_key']},
    'gemini': {'validate': validate_gemini, 'qualify': qualify_gemini, 'required': ['api_key']},
    'openai': {'validate': validate_openai, 'qualify': qualify_openai, 'required': ['api_key']},
}


def dispatch_validate(provider, credentials):
    if provider not in PROVIDERS:
        return {'ok': False, 'error': f'Unknown provider: {provider}. Use one of: {list(PROVIDERS.keys())}'}
    missing = [k for k in PROVIDERS[provider]['required'] if not (credentials or {}).get(k)]
    if missing:
        return {'ok': False, 'error': f'Missing credentials: {", ".join(missing)}'}
    return PROVIDERS[provider]['validate'](credentials)


def dispatch_qualify(provider, credentials, project):
    if provider not in PROVIDERS:
        return None, {'error': f'Unknown provider: {provider}'}
    missing = [k for k in PROVIDERS[provider]['required'] if not (credentials or {}).get(k)]
    if missing:
        return None, {'error': f'Missing credentials: {", ".join(missing)}'}
    return PROVIDERS[provider]['qualify'](credentials, project)
