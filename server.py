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
    """Test call to verify LLM provider credentials. Body: { provider, credentials }."""
    from qualification.providers import dispatch_validate

    body = request.get_json(silent=True) or {}
    provider = (body.get('provider') or '').strip().lower()
    credentials = body.get('credentials') or {}

    # Backward-compat: if request has Azure shape at the top level, treat as Azure
    if not provider and body.get('endpoint') and body.get('api_key') and body.get('deployment'):
        provider = 'azure'
        credentials = {
            'endpoint': body.get('endpoint'),
            'api_key': body.get('api_key'),
            'deployment': body.get('deployment'),
            'api_version': body.get('api_version', '2024-08-01-preview'),
        }

    if not provider:
        return jsonify({'ok': False, 'error': 'Missing provider (azure, anthropic, gemini, openai)'}), 400

    result = dispatch_validate(provider, credentials)
    status = 200 if result.get('ok') else 401
    return jsonify(result), status


@app.route('/api/qualify', methods=['POST'])
def qualify():
    """Live qualification via configured LLM provider. Body: { provider, credentials, project }."""
    from qualification.providers import dispatch_qualify

    body = request.get_json(silent=True) or {}
    provider = (body.get('provider') or '').strip().lower()
    credentials = body.get('credentials') or {}
    project = body.get('project') or {}

    # Backward-compat: Azure-shaped creds
    if not provider and credentials.get('endpoint') and credentials.get('deployment'):
        provider = 'azure'

    if not provider:
        return jsonify({'error': 'Missing provider (azure, anthropic, gemini, openai)'}), 400

    required = ['name', 'city', 'source', 'description', 'url']
    missing = [k for k in required if not project.get(k)]
    if missing:
        return jsonify({'error': f'Project missing fields: {", ".join(missing)}'}), 400

    qualification, meta = dispatch_qualify(provider, credentials, project)
    if qualification is None:
        return jsonify({'error': meta.get('error', 'Qualification failed'), 'meta': meta}), 502

    return jsonify({
        'qualification': qualification,
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

    # Use 'stat' reloader instead of 'watchdog' to avoid restart loops
    # triggered by installed-package activity in stdlib
    app.run(debug=True, port=5000, reloader_type='stat')
