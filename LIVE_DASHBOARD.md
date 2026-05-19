# Live Dashboard: Real-Time CSV Data

The Ärztehaus Radar dashboard now reads **live data from `output/leads.csv`** instead of hardcoded values.

---

## How It Works

1. **Python Flask Server** (`server.py`)
   - Reads `leads.csv` dynamically
   - Converts to JSON API
   - Serves HTML + API endpoint

2. **HTML Dashboard** (`output/dashboard-live.html`)
   - Fetches data from `/api/leads` endpoint
   - Renders in real-time
   - Updates whenever CSV changes

3. **Automatic Updates**
   - Run `python main.py` to regenerate `leads.csv`
   - Refresh dashboard page to see new data
   - No need to restart server

---

## Quick Start

### 1. Install Flask

```bash
pip install flask
# OR
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python server.py
```

Output:
```
============================================================
Ärztehaus Radar Dashboard Server
============================================================

Starting server on http://localhost:5000
Open in browser: http://localhost:5000

API endpoint: http://localhost:5000/api/leads

Press Ctrl+C to stop
============================================================
```

### 3. Open Dashboard

Open your browser to:
```
http://localhost:5000
```

The dashboard will load live data from `leads.csv` and display it beautifully.

---

## Workflow

### Scenario 1: View Current Results
```bash
# Terminal 1: Start server
python server.py

# Terminal 2 (or browser): Open
http://localhost:5000
```

### Scenario 2: Regenerate Data & View

```bash
# Terminal 1: Start server
python server.py

# Terminal 2: Generate new data
python main.py

# Browser: Refresh dashboard page
# (or click "Refresh Data" button)
```

The dashboard will show the newly qualified projects instantly.

---

## Features

✓ **Real-Time Data**: Reads from `output/leads.csv` (no manual sync)
✓ **API Endpoint**: `/api/leads` returns JSON with all projects + stats
✓ **Beautiful UI**: Professional styling, responsive design
✓ **Auto-Refresh**: Button to refresh without restarting
✓ **Summary Stats**: High/Medium/Low breakdown updated live
✓ **Project Details**: All fields displayed (confidence, suitability, reasoning)

---

## API Endpoint

If you want to query the data programmatically:

```bash
curl http://localhost:5000/api/leads | jq .
```

Returns:
```json
{
  "total": 10,
  "high": 2,
  "medium": 5,
  "low": 3,
  "leads": [
    {
      "Name": "Ärztezentrum Leipzig-Gohlis Neubau",
      "City": "Leipzig",
      "Source": "Developer Website",
      "Lead Quality": "high",
      "Confidence (%)": "98",
      "Physio Suitability (1-5)": "5",
      ...
    },
    ...
  ]
}
```

---

## For the Interview

This is **actually better** for demonstrating than static HTML:

1. **Shows System Thinking**: API layer, separation of concerns
2. **Real Data Integration**: Not hardcoded—demonstrates dynamic data handling
3. **Production-Ready**: This is how you'd build it for real use
4. **Live Demo**: You can run it live in the interview, regenerate data, show it updating

**In the interview:**
```bash
# Start server
python server.py

# In another terminal
python main.py

# Refresh browser to see new data load
```

Shows the system working end-to-end.

---

## Troubleshooting

### "Address already in use"
Port 5000 is in use. Either:
```bash
# Kill the process using port 5000
# Windows: netstat -ano | findstr :5000
# Then: taskkill /PID <PID> /F

# OR use different port
# Edit server.py: app.run(debug=True, port=5001)
```

### "Failed to load leads" error
- Make sure `output/leads.csv` exists
- Run `python main.py` first to generate data
- Check that Flask is installed: `pip install flask`

### Dashboard is blank
- Check browser console (F12 → Console) for errors
- Make sure server is running on port 5000
- Try refreshing the page

---

## File Structure

```
server.py                          # Flask server
output/
├── dashboard-live.html           # Live dashboard (reads from API)
├── dashboard.html                # Static version (hardcoded)
├── leads.csv                     # Data source
└── raw_projects.json             # Raw project data
```

---

## Why This Approach?

**Browser Limitation**: JavaScript in HTML can't read local files (CORS security). 

**Solution**: Use a simple Flask server that:
1. Reads the CSV file (no CORS issues)
2. Converts to JSON
3. Serves via HTTP (browsers can fetch this)
4. Dashboard fetches and renders

**Benefits**:
- Scalable (add more API endpoints later)
- Professional (API thinking)
- Interview-ready (can demo live)
- Real-world pattern (this is how production systems work)

---

## Next Enhancements

With more time, you could:
1. Add filtering/sorting UI
2. Add export to Airtable endpoint
3. Add webhook for automated updates
4. Add authentication
5. Store in database instead of CSV

All made easy by having an API layer.

---

**Now your dashboard reads real data. Perfect for the interview.** 🚀
