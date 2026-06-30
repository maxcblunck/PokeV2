# PokéValue

A local web app for Pokémon card valuation and investment analysis, with a built-in Frogger-style mini-game.

## Running the app

```bash
pip install -r requirements.txt
python -m uvicorn server:app --reload
```

Open **http://127.0.0.1:8000** in your browser.

Copy `.env.example` → `.env` and add your API keys:

```
POKEWALLET_API_KEY=...
POKETRACE_API_KEY=...
TCGPLAYER_PUBLIC_KEY=...
TCGPLAYER_PRIVATE_KEY=...
```

## Features

### Card Search & Valuation (`/search`)
- Search across a local database of 20,000+ English Pokémon cards
- Fetch live TCGPlayer prices via the **PokeWallet** and **PokeTrace** APIs
- **Composite score** (−100 to +100) built from 10 weighted signals:
  - Price vs. historical average, trend, momentum, volatility
  - Popularity, scarcity, pull odds, bid-ask spread, sale velocity, rarity baseline
- Buy / Hold / Sell recommendation with color-coded badge
- Plotly.js gauge chart + price history chart (last 10–20 sales)
- Market snapshot table (floor / mid / market / high) linked to TCGPlayer
- Variant switching for alternate printings (1st edition, shadowless, IRs, etc.)
- Falls back to simulated pricing if no live data is available

### Compare Cards (`/compare`)
- Search two cards and run valuations in a single request
- Side-by-side Plotly.js gauges and a bar chart scoring comparison
- Winner badge highlights the better buy

### Popularity Rankings (`/popularity`)
- Top 20 Pokémon by fan popularity score across all 1025 species
- Card images from the TCG image CDN; color-coded progress bars
- Database stats: total cards, distinct sets, rare card count, tracked species

### Collection Tracker (`/collection`)
- Register / log in (SQLite-backed, password-hashed)
- Add cards with condition grading (NM / LP / MP / HP / Damaged)
- Remove cards; card image grid persists across sessions via `localStorage`

### PokéCross (`/game`)
- Frogger-style canvas game embedded in the page
- Choose from 4 characters: Pikachu, Charmander, Bulbasaur, Squirtle
- Dodge cars (Snorlax / Rapidash / Doduo), ride Lapras logs, survive Rayquaza fly-bys
- Score = tiles advanced; difficulty scales with distance
- Best score persisted in browser `localStorage`
- Arrow keys / WASD on desktop; on-screen D-pad on mobile

## Architecture

```
server.py               # FastAPI app — lifespan startup, all API + page routes
static/
  index.html            # Redirect → /popularity
  popularity.html       # Top-20 grid + DB stats
  search.html           # Card search + Plotly.js gauge + price history
  compare.html          # Two-column search + Plotly.js bar chart
  collection.html       # Auth tabs + collection grid
  game.html             # Nav wrapper for the canvas game (iframes /game-content)
  style.css             # Pokémon dark theme (background #0d0f1a, gold #FFDE00)
  nav.js                # IIFE that injects the sticky nav into every page
game.html               # Self-contained canvas game (served at /game-content)
src/
  card_db.py            # Loads card JSON from data/cards/en/; search & filter
  scraper.py            # PokeWallet, PokeTrace, TCGPlayer API clients + disk caching
  analyzer.py           # 10-factor composite scoring engine; era/rarity/grade logic
  card_valuator.py      # Simulated pricing fallback (rarity base + multipliers)
  pokemon_popularity.py # Hardcoded popularity scores for all 1025 species
  db.py                 # SQLite — users + collection tables, auth helpers
  reporter.py           # CSV export, buy/sell formatting
data/
  cards/en/             # Card JSON files (one per set, ~20k cards)
  prices/results.csv    # Exported analysis results (gitignored)
```

**Data flow:** `CardDatabase` → `Scraper` (live) or `CardValuator` (simulated) → `Analyzer` (scoring) → JSON API → plain HTML/JS frontend

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server status + card count |
| GET | `/api/popularity` | Top-20 rankings + DB stats |
| GET | `/api/search?q=` | Card search by name |
| POST | `/api/analyze` | Full valuation for one card |
| POST | `/api/compare` | Parallel valuation for two cards |
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Log in, returns `{id, username}` |
| GET | `/api/collection/{user_id}` | List user's cards |
| POST | `/api/collection/{user_id}/add` | Add card to collection |
| DELETE | `/api/collection/{user_id}/{entry_id}` | Remove card |

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com) + [Uvicorn](https://www.uvicorn.org) — backend
- Plain HTML / CSS / JavaScript — frontend (no framework)
- [Plotly.js](https://plotly.com/javascript/) — gauge and chart rendering
- [PokeWallet API](https://pokewallet.com) — live TCGPlayer NM prices
- [PokeTrace API](https://poketrace.com) — secondary market sale history
- SQLite — user accounts and collection storage
- Pure JavaScript canvas game (no framework)
