#!/usr/bin/env python3
"""
Simple Flask server for Ärztehaus Radar dashboard
Serves HTML + provides JSON API for CSV data
"""
import json
import csv
from pathlib import Path
from flask import Flask, jsonify, send_file

app = Flask(__name__)

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
    """Serve the enhanced dashboard (default view with map + list views)."""
    return send_file('output/dashboard-enhanced.html')

@app.route('/list')
def dashboard_list():
    """Serve the list dashboard."""
    return send_file('output/dashboard-live.html')

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
