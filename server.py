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


# ── Static + page routes ─────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/popularity")
def page_popularity():
    return FileResponse("static/popularity.html")


@app.get("/search")
def page_search():
    return FileResponse("static/search.html")


@app.get("/compare")
def page_compare():
    return FileResponse("static/compare.html")


@app.get("/collection")
def page_collection():
    return FileResponse("static/collection.html")


@app.get("/game")
def page_game():
    return FileResponse("static/game.html")


@app.get("/game-content")
def page_game_content():
    return FileResponse("game.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
