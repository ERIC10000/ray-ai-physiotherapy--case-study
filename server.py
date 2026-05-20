#!/usr/bin/env python3
"""
Simple Flask server for Ärztehaus Radar dashboard
Serves HTML + provides JSON API for CSV data + live LLM qualification.
"""
import json
import csv
from pathlib import Path
from flask import Flask, jsonify, send_file, request

try:
    from flask_cors import CORS
    _has_cors = True
except ImportError:
    _has_cors = False

app = Flask(__name__)
if _has_cors:
    CORS(app, resources={r"/api/*": {"origins": "*"}})

def load_csv_data(csv_file="output/leads.csv"):
    """Load and parse CSV data into JSON."""
    try:
        data = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                row['Physio Suitability (1-5)'] = int(row['Physio Suitability (1-5)'])
                row['Confidence (%)'] = int(row['Confidence (%)'])
                data.append(row)
        return data
    except FileNotFoundError:
        return []

@app.route('/')
def dashboard():
    """Serve the professional dashboard with setup wizard + data collection + results."""
    return send_file('output/dashboard-pro.html')

@app.route('/classic')
def dashboard_classic():
    """Serve the previous enhanced dashboard (map + list views)."""
    return send_file('output/dashboard-enhanced.html')

@app.route('/list')
def dashboard_list():
    """Serve the list-only dashboard."""
    return send_file('output/dashboard-live.html')

@app.route('/map')
def dashboard_map():
    """Serve the map-only dashboard."""
    return send_file('output/dashboard-map.html')

@app.route('/api/leads')
def get_leads():
    """API endpoint for leads data."""
    leads = load_csv_data()

    # Calculate summary stats
    high_count = len([l for l in leads if l.get('Lead Quality') == 'high'])
    medium_count = len([l for l in leads if l.get('Lead Quality') == 'medium'])
    low_count = len([l for l in leads if l.get('Lead Quality') == 'low'])

    return jsonify({
        'total': len(leads),
        'high': high_count,
        'medium': medium_count,
        'low': low_count,
        'leads': leads
    })


@app.route('/api/validate', methods=['POST'])
def validate_credentials():
    """Make a small test call to verify Azure OpenAI credentials."""
    from qualification.azure_qualifier import validate_azure_credentials

    body = request.get_json(silent=True) or {}
    endpoint = (body.get('endpoint') or '').strip()
    api_key = (body.get('api_key') or '').strip()
    deployment = (body.get('deployment') or '').strip()
    api_version = (body.get('api_version') or '2024-08-01-preview').strip()

    if not endpoint or not api_key or not deployment:
        return jsonify({'ok': False, 'error': 'Missing endpoint, api_key, or deployment'}), 400

    result = validate_azure_credentials(endpoint, api_key, deployment, api_version)
    status = 200 if result.get('ok') else 401
    return jsonify(result), status


@app.route('/api/qualify', methods=['POST'])
def qualify():
    """
    Live qualification via Azure OpenAI.
    Body: { credentials: {...}, project: {name, city, source, description, url} }
    Returns: { qualification: {...}, meta: { latency_ms, tokens, raw_response } }
    """
    from qualification.azure_qualifier import qualify_project_azure

    body = request.get_json(silent=True) or {}
    creds = body.get('credentials') or {}
    project = body.get('project') or {}

    endpoint = (creds.get('endpoint') or '').strip()
    api_key = (creds.get('api_key') or '').strip()
    deployment = (creds.get('deployment') or '').strip()
    api_version = (creds.get('api_version') or '2024-08-01-preview').strip()

    if not endpoint or not api_key or not deployment:
        return jsonify({'error': 'Missing Azure credentials (endpoint, api_key, deployment)'}), 400

    required = ['name', 'city', 'source', 'description', 'url']
    missing = [k for k in required if not project.get(k)]
    if missing:
        return jsonify({'error': f'Project missing fields: {", ".join(missing)}'}), 400

    qualification, meta = qualify_project_azure(
        name=project['name'],
        city=project['city'],
        source=project['source'],
        description=project['description'],
        url=project['url'],
        endpoint=endpoint,
        api_key=api_key,
        deployment=deployment,
        api_version=api_version,
    )

    if qualification is None:
        return jsonify({'error': meta.get('error', 'Qualification failed'), 'meta': meta}), 502

    return jsonify({
        'qualification': qualification.to_dict(),
        'meta': {k: v for k, v in meta.items() if k != 'raw_response'},
        'raw_response': meta.get('raw_response'),
    })

if __name__ == '__main__':
    print("=" * 60)
    print("Ärztehaus Radar Dashboard Server")
    print("=" * 60)
    print("\nStarting server on http://localhost:5000")
    print("Open in browser: http://localhost:5000")
    print("\nAPI endpoint: http://localhost:5000/api/leads")
    print("\nPress Ctrl+C to stop")
    print("=" * 60 + "\n")

    app.run(debug=True, port=5000)
