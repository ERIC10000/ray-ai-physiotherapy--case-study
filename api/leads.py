"""
Vercel serverless function — serves leads.csv as JSON.
Mirrors the /api/leads endpoint from server.py for local Flask dev.
"""
from http.server import BaseHTTPRequestHandler
import json
import csv
import os


def load_csv_data(csv_path):
    """Load and parse CSV data into a list of dicts."""
    try:
        data = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row['Physio Suitability (1-5)'] = int(row.get('Physio Suitability (1-5)', 0))
                except (ValueError, TypeError):
                    row['Physio Suitability (1-5)'] = 0
                try:
                    row['Confidence (%)'] = int(row.get('Confidence (%)', 0))
                except (ValueError, TypeError):
                    row['Confidence (%)'] = 0
                data.append(row)
        return data
    except FileNotFoundError:
        return []


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Path resolution: api/leads.py → ../output/leads.csv
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            'output',
            'leads.csv'
        )

        leads = load_csv_data(csv_path)
        high = len([l for l in leads if l.get('Lead Quality') == 'high'])
        medium = len([l for l in leads if l.get('Lead Quality') == 'medium'])
        low = len([l for l in leads if l.get('Lead Quality') == 'low'])

        response = {
            'total': len(leads),
            'high': high,
            'medium': medium,
            'low': low,
            'leads': leads
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        return
