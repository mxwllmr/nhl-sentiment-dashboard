# NHL Sentiment Analysis Dashboard

A portfolio project demonstrating **live sentiment analysis** of NHL players using Reddit discussions and Claude AI.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.0+-red.svg)
![Claude API](https://img.shields.io/badge/Claude-API-purple.svg)

## Overview

This dashboard was built to **live-scrape** Reddit discussions from r/hockey and all 32 team subreddits, then analyze fan sentiment toward NHL players in real-time using Claude AI.

**Dataset:** Snapshot from May 2026 Playoffs (243 players analyzed). Some teams have limited coverage as data was collected during playoff season.

## Key Features

- **Live Reddit Scraping** - Real-time data collection from r/hockey + 32 team subs
- **AI-Powered Analysis** - Claude API for context-aware sentiment scoring
- **Player Sentiment Leaderboard** - Sortable rankings with team filtering
- **Team Sentiment Aggregation** - Average sentiment by team with visualizations
- **Player Detail Cards** - Individual analysis with summaries, themes, and notable quotes

## Technical Highlights

### Live Scraping Pipeline
The system was designed for real-time data collection:
1. **Fetch** - Scrape recent posts/comments from Reddit (rate-limited, retry-aware)
2. **Match** - Identify player mentions using smart name matching
3. **Analyze** - Send batched comments to Claude API for sentiment analysis
4. **Display** - Render results in interactive Streamlit dashboard

### Smart Player Matching
The scraper avoids false positives by:
- Matching full names ("Connor McDavid") and last names 5+ characters ("McDavid")
- Blocking common first names ("John", "Connor", "Ryan") from matching alone
- Handling accented characters (Tkachuk, Kaprizov, etc.)

### What the LLM Returns
For each player with sufficient mentions:
```json
{
  "sentiment_score": 0.65,
  "confidence": 0.8,
  "summary": "Fans are excited about his recent performance...",
  "themes": ["performance", "contract", "leadership"],
  "notable_quotes": ["Best player in the league right now"]
}
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Wikipedia     │────▶│  roster_scraper  │────▶│  players.json   │
│   (Rosters)     │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
┌─────────────────┐     ┌──────────────────┐              ▼
│     Reddit      │────▶│  reddit_scraper  │────▶┌─────────────────┐
│  (Comments)     │     │                  │     │  Group comments │
└─────────────────┘     └──────────────────┘     │   by player     │
                                                 └─────────────────┘
                                                          │
                                                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │   Claude API     │◀────│    Sentiment    │
                        │  (Analysis)      │     │    Analyzer     │
                        └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Streamlit     │
                                                 │   Dashboard     │
                                                 └─────────────────┘
```

## Installation & Usage

```bash
# Install dependencies
pip install streamlit pandas plotly requests beautifulsoup4 anthropic

# Run the dashboard
streamlit run dashboard.py
```

The dashboard loads pre-analyzed data automatically.

## Project Structure

```
nhl_sentiment_dashboard/
├── dashboard.py          # Streamlit dashboard (main app)
├── data_loader.py        # Player/team data loading
├── roster_scraper.py     # Wikipedia roster scraping
├── reddit_scraper.py     # Reddit comment collection
├── sentiment_analyzer.py # Claude API integration
├── players.json          # Current player roster
├── teams.json            # NHL team metadata
└── data/
    └── latest_results.json  # Analyzed sentiment data
```

## Sample Results

**Most Loved Players (May 2026):**
| Player | Team | Sentiment |
|--------|------|-----------|
| Connor McDavid | EDM | +0.72 |
| Cale Makar | COL | +0.68 |
| Connor Bedard | CHI | +0.61 |

**Team Sentiment Leaders:**
| Team | Avg Sentiment | Players Analyzed |
|------|---------------|------------------|
| Colorado Avalanche | +0.52 | 8 |
| Edmonton Oilers | +0.48 | 9 |

## Data Collection Note

**This project was built for live scraping.** The included dataset is a snapshot from the May 2026 playoffs, which is why some teams have limited coverage.

Reddit's API policies changed in mid-2026, now requiring OAuth authentication for programmatic access. The complete live scraping pipeline is included in the codebase (`reddit_scraper.py`, `historical_scraper.py`) and could be reactivated with Reddit API credentials via [PRAW](https://praw.readthedocs.io/).

## Skills Demonstrated

- **Web Scraping** - Rate-limited, retry-aware live data collection
- **API Integration** - Claude API for LLM-based text analysis
- **Data Pipeline Design** - Real-time ETL from raw comments to structured insights
- **Interactive Visualization** - Streamlit dashboard with Plotly charts
- **Sports Analytics** - Domain-specific NLP challenges (sarcasm, slang, context)

---

*Built as a sports analytics portfolio project. Data sourced from Reddit (r/hockey and team subreddits). Rosters from Wikipedia.*
