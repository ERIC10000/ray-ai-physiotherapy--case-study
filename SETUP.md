# Ärztehaus Radar: Setup & Usage Guide

## Quick Start (Demo Mode)

Run with realistic test data—no API key needed:

```bash
pip install -r requirements.txt
python main.py
```

Output: `output/leads.csv` with 10 qualified projects

---

## Real Mode (Live Data + Claude API)

### 1. Get Anthropic API Key

Get your Claude API key from [console.anthropic.com](https://console.anthropic.com/api-keys)

### 2. Set Environment Variable

**On Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-your-key-here"
python main.py --live
```

**On Windows (Command Prompt):**
```cmd
set ANTHROPIC_API_KEY=sk-ant-your-key-here
python main.py --live
```

**On Mac/Linux:**
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
python main.py --live
```

Or create `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Then run:
```bash
python main.py --live
```

---

## Output

All results are saved to `output/leads.csv`:

| Field | Example | Notes |
|-------|---------|-------|
| Name | Ärztezentrum Leipzig Zentrum-Ost | Project name |
| City | Leipzig | Target city |
| Source | Google News | Data source |
| Lead Quality | high | high/medium/low |
| Confidence | 95% | 0-100% confidence in assessment |
| Physio Suitability | 5/5 | Ground floor, size, accessibility |
| Estimated Stage | approval | concept → marketing |
| Ground Floor | Yes | Physiotherapy preference |
| Est. Size (sqm) | 380 | Target: 250–450 sqm |
| Accessibility | Yes | Wheelchair, parking |

---

## Data Sources

### Demo Mode
- 10 realistic German medical building projects
- Pre-qualified with mock LLM results
- For testing the pipeline

### Real Mode (--live)
1. **Google News RSS** — Healthcare building announcements (multi-state)
2. **Bing News** — Medical facility searches by city
3. **Developer Websites** — German healthcare real estate companies
4. **Berlin FIS-Broker** — Geospatial building data (Berlin-specific)

---

## Project Structure

```
.
├── main.py                              # Orchestrator
├── demo_data.json                       # 10 test projects
├── requirements.txt                     # Dependencies
│
├── scrapers/
│   ├── google_news_scraper.py          # News search (web)
│   ├── press_archive_scraper.py        # RSS feeds + Bing
│   └── berlin_portal_scraper.py        # FIS-Broker (Berlin)
│
├── qualification/
│   ├── schema.py                       # Qualification criteria
│   ├── llm_qualifier.py                # Claude API caller
│   └── demo_qualifier.py               # Mock evaluator
│
└── output/
    ├── csv_exporter.py                 # CSV writer
    ├── leads.csv                       # Results
    └── raw_projects.json               # Raw scraped data
```

---

## Qualification Criteria

Each project is scored on:

1. **Is it healthcare?** (not hospital, not residential)
2. **Is it a medical office building?** (Ärztehaus / medical center)
3. **Physiotherapy suitability (1-5):**
   - Ground floor access (critical)
   - Size: 250–450 sqm (ideal)
   - Accessibility (wheelchair, parking)
   - Location quality (foot traffic, parking, transit)
4. **Development stage:** concept → planning → approval → construction → marketing
5. **Lead quality:**
   - **High**: Confirmed Ärztehaus, ground floor, right size, early stage
   - **Medium**: Likely healthcare, some unknowns, decent stage
   - **Low**: Unclear fit, late stage, poor location/size
6. **Confidence:** 0–100% in the classification

---

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
You're in demo mode. This is normal for testing.
- To use live data: `set ANTHROPIC_API_KEY=your-key` then `python main.py --live`
- Or stay in demo mode: `python main.py`

### "No projects found"
- Check internet connection (for --live mode)
- Check that news sources are accessible
- Try demo mode: `python main.py`

### CSV is empty
- Ensure qualification ran successfully (check console output)
- Verify project data loaded correctly

### Unicode/Encoding errors on Windows
Windows console encoding may garble German characters (Ä, Ö, Ü).
- Data is stored correctly in CSV (open in Excel)
- This is a display issue, not a data issue

---

## Next Steps

### To add more data sources:
1. Create new scraper in `scrapers/`
2. Add to `get_all_projects()` in main.py
3. Test with `python main.py`

### To refine qualification:
1. Edit `QUALIFICATION_PROMPT` in `qualification/schema.py`
2. Test on a few projects
3. Re-run: `python main.py --live`

### To export to Airtable:
See `output/airtable_exporter.py` (stub)
- Add Airtable API key to `.env`
- Update exporter to push results

---

## Architecture Notes

**Why this design?**

1. **Modular**: Scrapers, qualification, output are independent
   - Easy to swap data sources
   - Easy to change LLM logic
   - Easy to add new output formats

2. **Demo-first**: Test without API key
   - Fast iteration
   - Cheap testing
   - No rate limit risk

3. **Real-mode ready**: Swap to Claude API in seconds
   - Set API key
   - Use `--live` flag
   - Same pipeline, real results

4. **Transparent**: CSV output is human-reviewable
   - Non-technical users can QA results
   - Easy to iterate on prompt
   - No black box

---

## AI-Native Building Process

This project was built using Claude at every step:

- **Design**: Claude helped design the qualification schema
- **Scraping**: Claude generated German search queries and scraping logic
- **LLM Prompt**: Iterative refinement of qualification criteria
- **Debugging**: Claude helped fix Python errors and dependencies
- **Testing**: Mock data and demo mode for zero-API-cost testing

The system itself uses Claude API for real qualification—it's AI-native both in *building* and *product*.
