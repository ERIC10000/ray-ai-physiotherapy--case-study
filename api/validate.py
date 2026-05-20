"""
Vercel serverless function — validates Azure OpenAI credentials with a tiny ping call.
"""
from http.server import BaseHTTPRequestHandler
import json
import time


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

        endpoint = (body.get('endpoint') or '').strip()
        api_key = (body.get('api_key') or '').strip()
        deployment = (body.get('deployment') or '').strip()
        api_version = (body.get('api_version') or '2024-08-01-preview').strip()

        if not endpoint or not api_key or not deployment:
            return self._send_json(400, {'ok': False, 'error': 'Missing endpoint, api_key, or deployment'})

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
                messages=[{'role': 'user', 'content': 'ping'}],
                max_tokens=5,
            )
            latency = int((time.time() - t0) * 1000)
            sample = (response.choices[0].message.content or '')[:30]
            return self._send_json(200, {
                'ok': True,
                'latency_ms': latency,
                'model': deployment,
                'sample_response': sample,
            })
        except Exception as e:
            return self._send_json(401, {'ok': False, 'error': f'{type(e).__name__}: {e}'})
