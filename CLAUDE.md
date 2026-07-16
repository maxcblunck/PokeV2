# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web app
python -m uvicorn server:app --reload

# Test PokéWallet API integration directly
python src/pokewallet_test.py
```

Open **http://127.0.0.1:8000** after starting the server.

## Architecture

**PokéValue** is a FastAPI web app for Pokémon card valuation and analysis. The entry point is `server.py`; pages are served as static HTML files from `static/`.

### Files

| File | Responsibility |
|---|---|
| `server.py` | FastAPI app — lifespan DB load, all `/api/*` endpoints, page routes serving static HTML |
| `static/popularity.html` | Top-20 popularity grid + DB stats |
| `static/search.html` | Card search + Plotly.js gauge + price chart + signal chips |
| `static/compare.html` | Two-column card compare + bar chart |
| `static/collection.html` | Auth (login/register) + card collection grid |
| `static/game.html` | Nav wrapper iframing the canvas game |
| `static/style.css` | Pokémon dark theme: `#0d0f1a` background, `#FFDE00` gold, `#CC0000` red |
| `static/nav.js` | IIFE that injects the sticky nav bar into every page |
| `game.html` | Self-contained canvas game served at `/game-content` |

### Core modules (`src/`)

| Module | Responsibility |
|---|---|
| `card_db.py` | Loads card JSON from `data/cards/en/` into a `CardDatabase`; search and filter |
| `scraper.py` | API clients for PokéWallet, PokeTrace, TCGPlayer; disk caching of sets/tokens |
| `cardsight.py` | CardSight AI client — real PSA graded sale medians via `pricing/search`; disk-cached (750/mo quota) |
| `psa.py` | PSA public API client — cert-number lookup (real grade + population) |
| `card_valuator.py` | Simulated pricing engine — rarity base prices + weighted multipliers |
| `analyzer.py` | 10-factor composite scoring: trend, popularity, scarcity, pull odds, volatility, etc. |
| `pokemon_popularity.py` | Static popularity scores for all 1025 species |
| `db.py` | SQLite — `users` + `collection` tables; `register_user`, `login_user`, collection CRUD |
| `reporter.py` | CSV export to `data/prices/results.csv`, buy/sell formatting |

### Data flow

`CardDatabase` → `Scraper` (live) or `CardValuator` (simulated) → `Analyzer` (scoring) → JSON API response → HTML/JS frontend renders with Plotly.js

## Git workflow

After completing any task, always run:

```bash
git add .
git commit -m "<concise description of what changed>"
git push
```

### Configuration

- API keys go in `.env`: `POKEWALLET_API_KEY`, `POKETRACE_API_KEY`, `TCGPLAYER_PUBLIC_KEY`, `TCGPLAYER_PRIVATE_KEY`, `CARDSIGHT_API_KEY` (real graded prices), `PSA_API_KEY` (cert lookup)
- `data/prices/results.csv` and `.env` are gitignored
