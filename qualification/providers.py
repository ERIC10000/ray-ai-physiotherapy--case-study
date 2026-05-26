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
City (from search context): {city}
Source: {source}
Description: {description}
URL: {url}

**Your Task:**
1. **Is this a healthcare/medical building?** (not hospital, not residential, not generic commercial)
2. **Is it specifically a medical office building (Ärztehaus) or similar?**
3. **Suitability for physiotherapy** (1-5 scale): ground floor, size 250-450 sqm, accessibility, location quality
4. **Estimated development stage**: concept / planning / approval / construction / marketing
5. **Lead quality** (high/medium/low)
6. **Confidence** (0-100%)
7. **Reasoning** (1-2 sentences)
8. **EXTRACT THE PROJECT'S LOCATION** — this is critical for map accuracy. Score follows location:
   - Read the title and description carefully — look for street names, house numbers, district names, town names, postal codes.
   - **Prefer the most specific combination of (street) + (district) + (city)** that the text supports — Nominatim resolves "Weitlingstraße, Berlin-Lichtenberg" much better than just "Berlin".
   - If a specific street is mentioned (e.g. "Müllerstraße", "Hauptbahnhof", "Alexanderplatz"), include it.
   - If a district is mentioned (e.g. "Berlin-Wedding", "Leipzig-Süd"), include it.
   - If a postal code (PLZ) appears (e.g. "10115 Berlin"), include it — these geocode very precisely.
   - Examples of good extractions (most specific first):
       "Müllerstraße 100, 13353 Berlin-Wedding"
       "Weitlingstraße, Berlin-Lichtenberg"
       "Berlin-Friedrichshain"
       "Neuenhagen bei Berlin"
   - NEVER invent or guess an address. Only return what the text actually contains.
   - The "City (from search context)" above is just a search keyword — the real project may be in a different town entirely. Trust the article text.
   - If no location at all is extractable, return null.

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
  "accessibility_noted": true|false|null,
  "extracted_location": "string with most specific location from the text, or null",
  "location_in_germany": true|false|null
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


# ----- Nominatim geocoding with disk cache --------------------------------
_GEOCODE_CACHE: dict = None
_GEOCODE_CACHE_PATH = None


def _load_geocode_cache():
    global _GEOCODE_CACHE, _GEOCODE_CACHE_PATH
    if _GEOCODE_CACHE is not None:
        return _GEOCODE_CACHE
    import os
    _GEOCODE_CACHE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'output',
        'geocode_cache.json',
    )
    try:
        with open(_GEOCODE_CACHE_PATH, 'r', encoding='utf-8') as f:
            _GEOCODE_CACHE = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _GEOCODE_CACHE = {}
    return _GEOCODE_CACHE


def _save_geocode_cache():
    if _GEOCODE_CACHE is None or _GEOCODE_CACHE_PATH is None:
        return
    try:
        import os
        os.makedirs(os.path.dirname(_GEOCODE_CACHE_PATH), exist_ok=True)
        with open(_GEOCODE_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(_GEOCODE_CACHE, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _classify_precision(osm_class: str, osm_type: str) -> str:
    if osm_class in ('building', 'amenity', 'shop', 'office') or osm_type in ('house', 'building'):
        return 'address'
    if osm_class == 'highway' or osm_type in ('road', 'street', 'residential', 'pedestrian', 'living_street'):
        return 'street'
    if osm_type in ('suburb', 'neighbourhood', 'quarter', 'borough', 'city_district', 'hamlet'):
        return 'district'
    if osm_type in ('city', 'town', 'village', 'municipality'):
        return 'city'
    return 'unverified'


def _nominatim_request(query: str) -> dict:
    """Single Nominatim call. Cached on disk."""
    import time, requests
    key = query.strip().lower()
    cache = _load_geocode_cache()
    if key in cache:
        return cache[key]

    headers = {
        'User-Agent': 'Aerztehaus-Radar/0.1 (case study; +https://github.com/ERIC10000/ray-ai-physiotherapy--case-study)',
        'Accept': 'application/json',
    }
    params = {
        'q': query,
        'format': 'json',
        'limit': '1',
        'countrycodes': 'de',
        'addressdetails': '1',
    }
    try:
        time.sleep(1.0)  # Nominatim TOS: max 1 req/sec
        r = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, timeout=10)
        r.raise_for_status()
        results = r.json()
    except Exception as e:
        result = {'verified': False, 'reason': f'{type(e).__name__}: {e}'}
        cache[key] = result
        _save_geocode_cache()
        return result

    if not results:
        result = {'verified': False, 'reason': 'no nominatim match'}
        cache[key] = result
        _save_geocode_cache()
        return result

    top = results[0]
    addr = top.get('address') or {}
    osm_class = top.get('class', '')
    osm_type = top.get('type', '')
    precision = _classify_precision(osm_class, osm_type)

    result = {
        'verified': precision in ('address', 'street', 'district'),
        'precision': precision,
        'lat': float(top['lat']),
        'lng': float(top['lon']),
        'display_name': top.get('display_name', ''),
        'class': osm_class,
        'type': osm_type,
        'importance': float(top.get('importance', 0) or 0),
        'matched_city': addr.get('city') or addr.get('town') or addr.get('village') or addr.get('municipality') or '',
        'matched_state': addr.get('state') or '',
        'query_used': query,
    }
    cache[key] = result
    _save_geocode_cache()
    return result


# Precision tier ordering (higher = more precise)
_PRECISION_RANK = {'address': 4, 'street': 3, 'district': 2, 'city': 1, 'unverified': 0}


def geocode_with_nominatim(query: str, fallback_city: str = '') -> dict:
    """
    Geocode a free-text location via Nominatim, trying multiple query variants
    and keeping the most precise result.

    Strategy:
      1. Try the query as-is (best case: street + district + city resolved together).
      2. If that returns only city-level, AND fallback_city was provided, try query + city.
      3. If query contains commas, also try just the first segment (often the street/district).

    Returns the highest-precision result found.
    """
    if not query or not isinstance(query, str):
        return {'verified': False, 'reason': 'empty query'}

    best = _nominatim_request(query)
    best_rank = _PRECISION_RANK.get(best.get('precision', 'unverified'), 0)

    # If we resolved at street/address level, no need to try more
    if best_rank >= 3:
        return best

    # Variant A: append a city hint if not already present
    if fallback_city and fallback_city.lower() not in query.lower():
        variant = f"{query}, {fallback_city}"
        alt = _nominatim_request(variant)
        if _PRECISION_RANK.get(alt.get('precision', 'unverified'), 0) > best_rank:
            best = alt
            best_rank = _PRECISION_RANK[alt['precision']]

    # Variant B: first segment of a comma-separated query (often the most specific bit)
    if ',' in query:
        first = query.split(',', 1)[0].strip()
        if first and first.lower() != query.lower():
            alt = _nominatim_request(first)
            if _PRECISION_RANK.get(alt.get('precision', 'unverified'), 0) > best_rank:
                best = alt
                best_rank = _PRECISION_RANK[alt['precision']]

    return best


def _enforce_verifiability_score(quality: str, confidence: int, precision: str) -> tuple[str, int, str]:
    """
    Enforce that lead quality reflects how verifiable the location is, but allow
    HIGH quality at district level (Berlin-Wedding, Leipzig-Süd etc. are
    legitimately actionable). Only city-centroid and unverified locations get
    materially downgraded.

        precision           max quality   max confidence   note
        ───────────────     ───────────   ──────────────   ───────────────────
        address             high          (no cap)         Exact building / house number
        street              high          (no cap)         Road-level — very actionable
        district            high          92               Neighbourhood-level — actionable
        city                medium        70               Only city centroid — approximate
        unverified          low           40               No Nominatim match

    Returns (adjusted_quality, adjusted_confidence, cap_reason_or_empty_string).
    """
    qrank = {'high': 3, 'medium': 2, 'low': 1}
    q = quality if quality in qrank else 'low'
    c = max(0, min(100, int(confidence)))

    if precision == 'address':
        return q, c, ''
    if precision == 'street':
        return q, c, ''
    if precision == 'district':
        # Keep quality; only mildly cap confidence
        return q, min(c, 92), ''
    if precision == 'city':
        # Honest downgrade: city-only is approximate, not actionable enough for "high"
        new_q = 'medium' if qrank[q] >= qrank['medium'] else q
        return new_q, min(c, 70), 'capped to medium — location only resolved to city centroid'
    # 'unverified' or anything else
    return 'low', min(c, 40), 'capped to low — no verifiable location'


def _to_qualification_dict(name, city, source, url, description, parsed):
    """Convert parsed JSON into the dashboard's expected lead shape, geocoding + score-enforcing."""
    gf = parsed.get('ground_floor_available')
    acc = parsed.get('accessibility_noted')

    extracted_location = parsed.get('extracted_location') or ''
    # Pass the search-context city as a fallback hint — geocoder will only use it
    # if the primary query returns a too-coarse result.
    geo = geocode_with_nominatim(extracted_location, fallback_city=city) if extracted_location else {'verified': False, 'reason': 'no location extracted'}

    # ---- Enforce verifiability-based scoring ----
    raw_quality = parsed.get('lead_quality', 'low')
    raw_confidence = int(parsed.get('confidence', 0))
    precision = geo.get('precision', 'unverified')
    adj_quality, adj_confidence, cap_reason = _enforce_verifiability_score(raw_quality, raw_confidence, precision)

    # Append capping note to reasoning so it's visible to the user
    reasoning = parsed.get('reasoning', '')
    if cap_reason:
        reasoning = f"{reasoning} [Score {cap_reason}]".strip()

    result_city = geo.get('matched_city') or city
    return {
        'Name': name,
        'City': result_city,
        'Source': source,
        'URL': url,
        'Description': description,
        'Is Healthcare Building': 'Yes' if parsed.get('is_healthcare_building') else 'No',
        'Medical Office Building': 'Yes' if parsed.get('is_medical_office_building') else 'No',
        'Physio Suitability (1-5)': int(parsed.get('suitability_for_physio', 1)),
        'Estimated Stage': parsed.get('estimated_stage', 'unknown'),
        # Quality + confidence are now ENFORCED by location verifiability:
        # high requires address/street, medium requires district, anything else → low.
        'Lead Quality': adj_quality,
        'Confidence (%)': adj_confidence,
        'Reasoning': reasoning,
        'Ground Floor': 'Yes' if gf else ('No' if gf is False else 'Unknown'),
        'Est. Size (sqm)': parsed.get('estimated_sqm') or 'Unknown',
        'Accessibility': 'Yes' if acc else ('No' if acc is False else 'Unknown'),
        # ----- Geographic verification fields -----
        'Extracted Location': extracted_location,
        'Geocoded Address': geo.get('display_name', ''),
        'Geocode Precision': precision,
        'Location Verified': geo.get('verified', False),
        'Latitude': geo.get('lat'),
        'Longitude': geo.get('lng'),
        # ----- Score-adjustment transparency -----
        'AI Quality (raw)': raw_quality,
        'AI Confidence (raw)': raw_confidence,
        'Score Cap Reason': cap_reason,
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
