"""
Vercel serverless function — qualifies one project via any supported LLM provider.
Supports: azure, anthropic, gemini, openai.
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


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

        provider = (body.get('provider') or '').strip().lower()
        credentials = body.get('credentials') or {}
        project = body.get('project') or {}

        if not provider and credentials.get('endpoint') and credentials.get('deployment'):
            provider = 'azure'

        if not provider:
            return self._send_json(400, {'error': 'Missing provider (azure, anthropic, gemini, openai)'})

        required = ['name', 'city', 'source', 'description', 'url']
        missing = [k for k in required if not project.get(k)]
        if missing:
            return self._send_json(400, {'error': f'Project missing fields: {", ".join(missing)}'})

        try:
            from qualification.providers import dispatch_qualify
            qualification, meta = dispatch_qualify(provider, credentials, project)
        except Exception as e:
            return self._send_json(500, {'error': f'Server error: {type(e).__name__}: {e}'})

        if qualification is None:
            return self._send_json(502, {'error': meta.get('error', 'Qualification failed'), 'meta': meta})

        return self._send_json(200, {
            'qualification': qualification,
            'meta': {k: v for k, v in meta.items() if k != 'raw_response'},
            'raw_response': meta.get('raw_response'),
        })
