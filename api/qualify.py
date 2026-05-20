"""
Vercel serverless function — qualifies one project via Azure OpenAI.
Self-contained (no imports from qualification/ module) so Vercel bundles only what's needed.
"""
from http.server import BaseHTTPRequestHandler
import json
import time
import re


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


def qualify_to_dict(name, city, source, url, description, parsed):
    """Convert parsed JSON into the same shape as ProjectQualification.to_dict."""
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


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(length) if length > 0 else b'{}'
            body = json.loads(raw.decode('utf-8') or '{}')
        except Exception as e:
            return self._send_json(400, {'error': f'Invalid JSON: {e}'})

        creds = body.get('credentials') or {}
        project = body.get('project') or {}

        endpoint = (creds.get('endpoint') or '').strip()
        api_key = (creds.get('api_key') or '').strip()
        deployment = (creds.get('deployment') or '').strip()
        api_version = (creds.get('api_version') or '2024-08-01-preview').strip()

        if not endpoint or not api_key or not deployment:
            return self._send_json(400, {'error': 'Missing Azure credentials (endpoint, api_key, deployment)'})

        required = ['name', 'city', 'source', 'description', 'url']
        missing = [k for k in required if not project.get(k)]
        if missing:
            return self._send_json(400, {'error': f'Project missing fields: {", ".join(missing)}'})

        prompt = QUALIFICATION_PROMPT.format(
            name=project['name'],
            city=project['city'],
            source=project['source'],
            description=project['description'],
            url=project['url'],
        )

        try:
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint.rstrip('/'),
            )
            t0 = time.time()
            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {'role': 'system', 'content': 'You are an expert in real estate qualification. Always respond with valid JSON only.'},
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.2,
                max_tokens=600,
                response_format={'type': 'json_object'},
            )
            latency = int((time.time() - t0) * 1000)
            response_text = response.choices[0].message.content or ''

            # Parse JSON
            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                m = re.search(r'\{[\s\S]*\}', response_text)
                if not m:
                    return self._send_json(502, {'error': 'No JSON object in response', 'raw_response': response_text})
                parsed = json.loads(m.group(0))

            qualification = qualify_to_dict(
                project['name'], project['city'], project['source'],
                project['url'], project['description'], parsed,
            )

            return self._send_json(200, {
                'qualification': qualification,
                'meta': {
                    'provider': 'azure-openai',
                    'deployment': deployment,
                    'latency_ms': latency,
                    'tokens_in': response.usage.prompt_tokens if response.usage else None,
                    'tokens_out': response.usage.completion_tokens if response.usage else None,
                },
                'raw_response': response_text,
            })

        except Exception as e:
            return self._send_json(502, {'error': f'{type(e).__name__}: {e}'})
