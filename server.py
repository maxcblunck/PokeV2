import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

_db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db
    from src.card_db import CardDatabase
    from src.db import init_db
    _db = CardDatabase()
    init_db()
    print(f"[server] Loaded {len(_db._cards):,} cards")
    yield


app = FastAPI(title="PokéValue", lifespan=lifespan)


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "cards": len(_db._cards) if _db else 0}


# ── Popularity ───────────────────────────────────────────────────────────────

@app.get("/api/popularity")
def popularity():
    from src.pokemon_popularity import POPULARITY_SCORES

    ranked = sorted(
        [{"name": k, "score": v} for k, v in POPULARITY_SCORES.items()],
        key=lambda r: r["score"],
        reverse=True,
    )
    top20 = ranked[:20]

    for entry in top20:
        matches = _db.search_card(entry["name"])
        entry["image_url"] = None
        if matches:
            det = _db.get_card_details(
                matches[0]["name"], matches[0]["set_name"], matches[0].get("number")
            )
            if det and det.get("images"):
                entry["image_url"] = det["images"].get("small")

    all_cards = _db._cards
    total_sets = len({c.get("set_name") for c in all_cards})
    rare_count = len(_db.get_rare_cards())

    return {
        "top20": top20,
        "stats": {
            "total_cards": len(all_cards),
            "total_sets": total_sets,
            "rare_count": rare_count,
            "tracked_species": len(POPULARITY_SCORES),
        },
    }


# ── Search ───────────────────────────────────────────────────────────────────

@app.get("/api/search")
def search(q: str = Query(..., min_length=1)):
    return _db.search_card(q)


# ── Analyze ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    card_name: str
    set_name: str
    number: str | None = None
    card_id: str | None = None


def _run_analysis(req: AnalyzeRequest) -> dict:
    from src.scraper import get_card_prices
    from src.analyzer import analyze_card

    details = _db.get_card_details(req.card_name, req.set_name, req.number)
    card_id = req.card_id or (details.get("id") if details else None)
    label = f"{req.card_name} ({req.set_name})"

    prices = get_card_prices(label, card_id)
    if not prices:
        raise HTTPException(status_code=404, detail="No price data available for this card.")

    first = prices[0]
    is_pw = first.get("source") == "pokewallet"
    variant_name = first.get("sub_type_name", "") if is_pw else ""

    analysis = analyze_card(label, prices, details, variant=variant_name)

    all_variants = first.get("all_variants", []) if is_pw else []
    active = all_variants[0] if all_variants else first
    market = active.get("market_price") or first.get("market_price")
    low    = active.get("low_price")    or first.get("low_price")
    mid    = active.get("mid_price")    or first.get("mid_price")
    high   = active.get("high_price")   or first.get("high_price")

    raw_prices = []
    for p in prices:
        m = re.search(r"\d+\.?\d*", str(p.get("price", "")).replace(",", ""))
        if m:
            raw_prices.append(float(m.group()))

    return {
        "analysis": analysis,
        "details": {
            "id":     (details or {}).get("id") or card_id,
            "rarity": (details or {}).get("rarity"),
            "types":  (details or {}).get("types", []),
            "images": (details or {}).get("images", {}),
        },
        "market_price":  market,
        "low_price":     low,
        "mid_price":     mid,
        "high_price":    high,
        "all_variants":  all_variants,
        "raw_prices":    raw_prices,
        "data_source":   first.get("data_source", "simulated"),
        "tcg_url":       first.get("url"),
    }


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    return _run_analysis(req)


# ── Compare ──────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    card_a: AnalyzeRequest
    card_b: AnalyzeRequest


@app.post("/api/compare")
def compare(req: CompareRequest):
    return {
        "a": _run_analysis(req.card_a),
        "b": _run_analysis(req.card_b),
    }


# ── Auth ─────────────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register")
def register(req: AuthRequest):
    from src.db import register_user
    ok, msg = register_user(req.username, req.password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/api/auth/login")
def login(req: AuthRequest):
    from src.db import login_user
    user = login_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return user


# ── Collection ───────────────────────────────────────────────────────────────

class AddCardRequest(BaseModel):
    card_name: str
    set_name: str
    set_code: str | None = None
    number: str | None = None
    rarity: str | None = None
    condition: str = "NM"


@app.get("/api/collection/{user_id}")
def get_collection(user_id: int):
    from src.db import get_collection as _get
    return _get(user_id)


@app.post("/api/collection/{user_id}/add")
def add_to_collection(user_id: int, req: AddCardRequest):
    from src.db import add_to_collection as _add
    details = _db.get_card_details(req.card_name, req.set_name, req.number)
    card_dict = {
        "id":       (details or {}).get("id", ""),
        "name":     req.card_name,
        "set_name": req.set_name,
        "set_code": req.set_code or "",
        "number":   req.number or "",
        "rarity":   req.rarity or "",
        "images":   (details or {}).get("images", {}),
    }
    entry_id = _add(user_id, card_dict, req.condition)
    return {"id": entry_id}


@app.delete("/api/collection/{user_id}/{entry_id}")
def remove_from_collection(user_id: int, entry_id: int):
    from src.db import remove_from_collection as _remove
    _remove(user_id, entry_id)
    return {"ok": True}


# ── Portfolio ────────────────────────────────────────────────────────────────

# Fraction of NM market value retained at each condition grade.
_CONDITION_MULTIPLIER = {
    "NM":      1.00,
    "LP":      0.85,
    "MP":      0.70,
    "HP":      0.50,
    "Damaged": 0.30,
}

# Composite score → 1-line verdict bucket (mirrors analyzer thresholds).
def _verdict_bucket(score: float | None) -> str:
    if score is None:
        return "No Data"
    if score >= 60:  return "Strong Sell"
    if score >= 25:  return "Sell"
    if score > -25:  return "Hold"
    if score > -60:  return "Buy"
    return "Strong Buy"


@app.get("/api/portfolio/{user_id}")
def get_portfolio(user_id: int):
    """
    Return the user's holdings and value-history WITHOUT pricing any cards.
    Live valuation is deferred to POST /api/portfolio/{user_id}/value so the
    page loads instantly and the pricing APIs are only hit on demand.
    """
    from src.db import get_collection as _get, get_snapshots

    cards = _get(user_id)
    total_sets = len({c.get("set_name") for c in cards if c.get("set_name")})
    return {
        "cards": cards,
        "stats": {
            "card_count": len(cards),
            "set_count":  total_sets,
        },
        "history": get_snapshots(user_id),
    }


@app.post("/api/portfolio/{user_id}/value")
def value_portfolio(user_id: int):
    """
    Value every card in the user's collection through the live/simulated
    pricing engine, record a daily snapshot, and return per-card valuations
    plus aggregate stats. Called on demand (button click), never on page load.
    """
    from src.db import get_collection as _get, record_snapshot, get_snapshots

    cards = _get(user_id)
    valued = []
    total_value = 0.0
    score_sum = 0.0
    scored_n = 0
    buckets: dict[str, int] = {}

    for c in cards:
        cond = c.get("condition", "NM")
        mult = _CONDITION_MULTIPLIER.get(cond, 1.0)
        req = AnalyzeRequest(
            card_name=c["card_name"],
            set_name=c.get("set_name") or "",
            number=c.get("card_number") or None,
            card_id=c.get("card_id") or None,
        )
        try:
            res = _run_analysis(req)
            market = res.get("market_price")
            score = (res.get("analysis") or {}).get("composite_score")
            rec = (res.get("analysis") or {}).get("recommendation")
        except HTTPException:
            market, score, rec = None, None, None
        except Exception:
            market, score, rec = None, None, None

        value = round(market * mult, 2) if market else None
        if value:
            total_value += value
        if score is not None:
            score_sum += score
            scored_n += 1
        bucket = _verdict_bucket(score)
        buckets[bucket] = buckets.get(bucket, 0) + 1

        valued.append({
            "entry_id":       c["id"],
            "card_name":      c["card_name"],
            "set_name":       c.get("set_name"),
            "card_number":    c.get("card_number"),
            "rarity":         c.get("rarity"),
            "condition":      cond,
            "image_url":      c.get("image_url"),
            "market_price":   market,
            "value":          value,
            "composite_score": score,
            "recommendation": rec or "Insufficient Data",
        })

    record_snapshot(user_id, total_value, len(cards))

    avg_score = round(score_sum / scored_n, 1) if scored_n else None
    priced = [v for v in valued if v["value"]]
    most_valuable = max(priced, key=lambda v: v["value"], default=None)
    best_buy = min(
        (v for v in valued if v["composite_score"] is not None),
        key=lambda v: v["composite_score"], default=None,
    )
    top_sell = max(
        (v for v in valued if v["composite_score"] is not None),
        key=lambda v: v["composite_score"], default=None,
    )

    return {
        "cards": valued,
        "stats": {
            "total_value":    round(total_value, 2),
            "card_count":     len(cards),
            "priced_count":   len(priced),
            "avg_score":      avg_score,
            "overall_verdict": _verdict_bucket(avg_score),
        },
        "buckets": buckets,
        "highlights": {
            "most_valuable": most_valuable,
            "best_buy":      best_buy,
            "top_sell":      top_sell,
        },
        "history": get_snapshots(user_id),
    }


# ── Static + page routes ─────────────────────────────────────────────────────

def _page(path: str) -> FileResponse:
    r = FileResponse(path)
    r.headers["Cache-Control"] = "no-store"
    return r


@app.get("/")
def root():
    return _page("static/index.html")


@app.get("/search")
def page_search():
    return _page("static/search.html")


@app.get("/compare")
def page_compare():
    return _page("static/compare.html")


@app.get("/collection")
def page_collection():
    return _page("static/collection.html")


@app.get("/portfolio")
def page_portfolio():
    return _page("static/portfolio.html")


@app.get("/game")
def page_game():
    return _page("static/game.html")


@app.get("/game-content")
def page_game_content():
    return _page("game.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
