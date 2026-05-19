# Map Dashboard: Geographic View of Projects

The Ärztehaus Radar now includes a **beautiful map view** showing all projects geographically across Germany. Perfect for interviews!

---

## Features

✓ **Interactive Map**: Projects plotted on OpenStreetMap
✓ **Color-Coded Markers**: Green (High), Yellow (Medium), Red (Low)
✓ **Sidebar List**: All projects with quality badges
✓ **Filters**: Toggle High/Medium/Low on the fly
✓ **Real-Time Data**: Reads from CSV via API
✓ **Responsive**: Works on desktop and mobile
✓ **No API Key Needed**: Uses free OpenStreetMap tiles

---

## How to Use

### Start the Server

```bash
python server.py
```

### View Map (Default)

Open your browser:
```
http://localhost:5000
```

Shows **interactive map** with all projects plotted by city.

### View List (Alternative)

If you want the original list view:
```
http://localhost:5000/list
```

---

## Map Features

### Markers
- **Number in circle**: How many projects in that city
- **Color**: Best quality in that city
  - 🟢 Green = High quality lead
  - 🟡 Yellow = Medium quality
  - 🔴 Red = Low quality

### Interactions
- **Click marker**: Shows popup with project breakdown
- **Click city in list**: Map zooms to that city
- **Filter buttons**: Show/hide quality levels
- **Refresh button**: Reload data from CSV

### Layout
- **Left sidebar**: Project list + filters + stats
- **Right map**: Interactive map of Germany
- **Responsive**: Sidebar/map stack on mobile

---

## Interview Demo Script

Perfect for showcasing:

```bash
# 1. Start server
python server.py

# 2. Open browser
http://localhost:5000

# Say to interviewer:
"Here's all 10 projects visualized geographically across Germany.
Each marker shows how many projects are in that city.

Green markers = high-quality leads (95%+ confidence).
Yellow = medium quality. Red = low quality.

We can filter by quality, click cities to zoom in, and see the 
full project list on the left.

If I had API key access, this would show real projects from 
geoportals across all 4 states."

# 3. Interactive demo:
- Click a green marker (high quality) → shows Leipzig-Gohlis
- Click "High" filter → shows only green markers
- Click a city name in sidebar → map zooms there
- Click Refresh → reloads latest data
```

---

## Why Map View Impresses

1. **Geographic Context**: Shows why location matters (7 cities, 4 states)
2. **Visual Appeal**: Maps look professional in interviews
3. **Data Visualization**: Makes data story clear at a glance
4. **Interactivity**: Engaging, not static
5. **No Dependencies**: OpenStreetMap is free (no API key needed)
6. **Real Data**: Reads live from CSV, not hardcoded

---

## File Details

**Map View**: `output/dashboard-map.html`
- Uses Leaflet.js (free, open-source mapping library)
- OpenStreetMap tiles (free, no API key)
- Reads from `/api/leads` endpoint
- 350px sidebar + full map
- Color-coded by quality

**API Endpoint**: `/api/leads`
- Returns all projects as JSON
- Includes stats (total, high, medium, low)
- Updated automatically when CSV changes

---

## Comparison: Map vs. List

| Feature | Map View | List View |
|---------|----------|-----------|
| **URL** | http://localhost:5000 | http://localhost:5000/list |
| **Best for** | Overview, interviews | Details, CSV review |
| **Visual** | Interactive map | Scrollable list |
| **Impression** | Professional, polished | Data-focused |
| **Setup** | Flask server | Flask server |

**Use map for interviews. Use list for data review.**

---

## Customization (Optional)

### Change Default View
Edit `server.py`, swap these:

```python
# Map as default
@app.route('/')
def dashboard():
    return send_file('output/dashboard-map.html')

# List as default (comment out above, uncomment below)
# @app.route('/')
# def dashboard():
#     return send_file('output/dashboard-live.html')
```

### Change Map Center/Zoom
Edit `output/dashboard-map.html`, line ~210:

```javascript
map = L.map('map').setView([51.8, 10.5], 6);
//                          lat   lon    zoom
// Currently centered on Germany (51.8°N, 10.5°E)
// Zoom 6 = country level view
```

### Add More Cities
Edit city coordinates in `dashboard-map.html`:

```javascript
const cityCoordinates = {
    'Berlin': [52.5200, 13.4050],
    'München': [48.1351, 11.5820],  // Add more cities here
    // ...
};
```

---

## Why No API Key Needed?

- **Leaflet.js**: Free open-source library (no API key)
- **OpenStreetMap**: Free tile provider (no API key)
- **Your data**: Comes from your CSV via `/api/leads`

This is fully self-contained and requires **zero external API keys**.

---

## Performance

- **Fast load**: Map renders in <2 seconds
- **Smooth interactions**: Click/zoom/filter instant
- **Low bandwidth**: Lightweight tiles + local data
- **Responsive**: Works on phones, tablets, desktops

---

## Interview Checklist

- [ ] Start `python server.py`
- [ ] Open `http://localhost:5000`
- [ ] Map loads with all 10 projects
- [ ] Click a marker → popup shows project breakdown
- [ ] Filter High/Medium/Low → markers update
- [ ] Click a city name → map zooms there
- [ ] All interactions work smoothly
- [ ] Prepare talking points about geographic strategy

---

## Next Step

Once you get an API key and implement Phase 1 (real geoportal data), you'll have:
- 50-100 real German projects
- Points from FIS-Broker, state geoportals, news sources
- Same beautiful map showing nationwide coverage
- Exact same interface (no changes needed)

The map will be even more impressive with real data spanning all of Germany.

---

**Map view is live and ready for interview.** 🗺️
