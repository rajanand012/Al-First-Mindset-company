# AI-First Mindset Assessment Tool

A web-based tool that evaluates manufacturing companies' AI maturity using a structured, consistent scoring rubric powered by the Claude API.

## Features

- **Minimal input required** — just company name and website URL
- **Automated web scanning** — scrapes homepage + key subpages (about, products, technology, etc.)
- **7-day content caching** — same website data produces identical scores within the cache window
- **Structured rubric** — 10 discrete categories scored 1-5 (not holistic guesswork)
- **Temperature 0** — deterministic Claude API calls eliminate LLM randomness
- **Persistent storage** — SQLite database tracks all assessments for comparison over time
- **Score trending** — view previous scores alongside new ones to track AI maturity progress

## Scoring Categories (10 categories, 1-5 each, max 50 → scaled to 100%)

| # | Category | What It Measures |
|---|----------|-----------------|
| 1 | AI Presence on Website | How prominently AI is mentioned across the site |
| 2 | AI-Powered Products & Services | AI/ML-enhanced product offerings |
| 3 | Smart Manufacturing & Industry 4.0 | AI in manufacturing processes (predictive maintenance, digital twins, etc.) |
| 4 | Data Strategy & Analytics | Evidence of data-driven decision making |
| 5 | AI Talent & Team | Investment in AI roles, teams, partnerships |
| 6 | AI Innovation & R&D | AI research, patents, innovation labs |
| 7 | AI in Customer Experience | Chatbots, personalization, AI-powered support |
| 8 | AI in Supply Chain & Operations | AI in logistics, forecasting, inventory |
| 9 | AI Strategy & Vision | Published AI strategy and roadmap |
| 10 | Responsible AI & Governance | AI ethics, governance frameworks, transparency |

## Grading Scale

| Grade | Score Range | Label |
|-------|-----------|-------|
| A+ | 90-100% | AI-First Leader |
| A | 80-89% | AI-Advanced |
| B+ | 70-79% | AI-Proficient |
| B | 60-69% | AI-Developing |
| C+ | 50-59% | AI-Aware |
| C | 40-49% | AI-Exploring |
| D | 30-39% | AI-Beginner |
| F | 0-29% | AI-Absent |

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Run the app
python app.py
```

Open http://localhost:5000 in your browser.

## Consistency Guarantees

With the built-in consistency features, expect **90%+ scoring consistency** for unchanged websites:

1. **Web caching (7 days)** — identical input data within the cache window
2. **Structured rubric** — 10 discrete 1-5 scores instead of holistic judgment
3. **Temperature 0** — deterministic LLM output
4. **Stored results** — compare current vs. previous scores side by side

## Tech Stack

- **Backend:** Python / Flask
- **AI:** Claude API (Anthropic) with temperature=0
- **Database:** SQLite
- **Frontend:** Bootstrap 5
- **Scraping:** requests + BeautifulSoup4
