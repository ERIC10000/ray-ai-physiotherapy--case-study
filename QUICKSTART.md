# Ärztehaus Radar: Quick Start (2 Min)

## Demo Mode (Test Immediately)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Run
python main.py

# 3. Check output
output/leads.csv
```

Output: 10 qualified demo projects (high/medium/low mix)

---

## Live Mode (Real Data + Claude API)

```bash
# 1. Get API key from console.anthropic.com

# 2. Set environment (Windows PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-your-key-here"

# 3. Run live
python main.py --live

# 4. Check output
output/leads.csv
```

---

## What You Get

| Top Leads (High Quality) |
|---------|
| Ärztezentrum Leipzig-Gohlis (98% confidence) |
| Medical Office Berlin-Charlottenburg (92% confidence) |
| More (medium quality) |

**CSV columns:**
- Name, City, Source, Lead Quality, Confidence, Suitability (1-5), Stage, Ground Floor, Size (sqm), Accessibility, Reasoning

---

## What It Does

```
1. SCRAPE → Discovers projects from news, geoportals, developer sites
2. QUALIFY → Claude API scores for physiotherapy suitability
3. OUTPUT → CSV with high/medium/low leads + reasoning
```

Target: 7 German cities (Berlin, Leipzig, Dresden, etc.)
Suitability: Ground floor, 250–450 sqm, accessible, good location

---

## File Structure

```
main.py                  # Entry point (orchestrator)
demo_data.json           # 10 test projects
requirements.txt         # Dependencies (anthropic, requests, beautifulsoup4)

scrapers/                # Data collection
  ├─ google_news_scraper.py
  ├─ press_archive_scraper.py
  └─ berlin_portal_scraper.py

qualification/           # LLM classification
  ├─ schema.py          # Criteria definition
  ├─ llm_qualifier.py   # Claude API caller
  └─ demo_qualifier.py  # Mock evaluator

output/
  ├─ csv_exporter.py    # Export to CSV
  └─ leads.csv          # Results
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API key not found" | Demo mode (normal). Add key + `--live` for real data. |
| No projects found | Check internet (--live) or try demo mode. |
| CSV is empty | Check console for errors. Try demo mode first. |
| German characters garbled | Display issue (data is fine). Open CSV in Excel. |

---

## Next Steps

**To use real data:**
1. Set `ANTHROPIC_API_KEY`
2. Run `python main.py --live`
3. Wait for web scraping (1–2 min)
4. Review `output/leads.csv`

**To add more sources:**
1. Create new scraper in `scrapers/`
2. Call it in `main.py`
3. Re-run

**To refine qualification:**
1. Edit `QUALIFICATION_PROMPT` in `qualification/schema.py`
2. Re-run: `python main.py --live`
3. Evaluate results

---

## More Info

- **SETUP.md** — Full installation & configuration
- **APPROACH.md** — Design decisions & rationale
- **README.md** — Project overview

---

**GitHub**: https://github.com/ERIC10000/ray-ai-physiotherapy--case-study
**Status**: MVP complete, 10 demo projects, ready for real data
