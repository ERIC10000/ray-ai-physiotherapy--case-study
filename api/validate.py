"""
Vercel serverless function — validates LLM provider credentials.
Supports: azure, anthropic, gemini, openai.
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Make qualification module importable from the Vercel function bundle
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
            return self._send_json(400, {'ok': False, 'error': f'Invalid JSON: {e}'})

        provider = (body.get('provider') or '').strip().lower()
        credentials = body.get('credentials') or {}

        # Backward-compat: Azure shape at top level
        if not provider and body.get('endpoint') and body.get('api_key') and body.get('deployment'):
            provider = 'azure'
            credentials = {
                'endpoint': body.get('endpoint'),
                'api_key': body.get('api_key'),
                'deployment': body.get('deployment'),
                'api_version': body.get('api_version', '2024-08-01-preview'),
            }

        if not provider:
            return self._send_json(400, {'ok': False, 'error': 'Missing provider (azure, anthropic, gemini, openai)'})

        try:
            from qualification.providers import dispatch_validate
            result = dispatch_validate(provider, credentials)
        except Exception as e:
            return self._send_json(500, {'ok': False, 'error': f'Server error: {type(e).__name__}: {e}'})

        status = 200 if result.get('ok') else 401
        return self._send_json(status, result)
