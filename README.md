# Ärztehaus Radar: AI-Native Medical Building Discovery

An MVP system to discover medical (Ärztehaus) building developments across Berlin, Brandenburg, Saxony-Anhalt, and Saxony, qualify them for physiotherapy suitability, and output structured leads.

## How It Works

```
1. SCRAPE → Collect projects from 3 sources (Google News, Berlin FIS-Broker, healthcare press)
2. QUALIFY → LLM scores each project against suitability criteria
3. OUTPUT → Results in Airtable (+ CSV backup)
```

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Output: Airtable table + `output/leads.csv`

## Project Structure

```
scrapers/
├── google_news_scraper.py      # Healthcare building announcements
├── berlin_portal_scraper.py    # FIS-Broker geospatial data
└── healthcare_press_scraper.py # LinkedIn + developer sites

qualification/
├── schema.py                   # Qualification criteria
└── llm_qualifier.py           # Claude API qualification

output/
├── airtable_exporter.py       # Push to Airtable
└── csv_exporter.py            # CSV fallback

main.py                         # Orchestrator
```

## Target Cities

Berlin, Potsdam, Cottbus, Magdeburg, Halle (Saale), Leipzig, Dresden

## Evaluation Criteria (LLM)

- Is it a medical/healthcare building?
- Suitability for physiotherapy (ground floor, 250–450 sqm, accessibility)
- Estimated stage (concept/planning/approval/construction/marketing)
- Lead quality (high/medium/low)
- Confidence score
