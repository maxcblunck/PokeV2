"""
CardSight AI pricing client — real graded (PSA) sale prices.

Two-step canonical lookup (far more grade-accurate than free-text title search):

  1. Resolve the card to a CardSight UUID:
       GET /v1/catalog/search?q=<name number>&type=card
  2. Pull structured pricing for that UUID:
       GET /v1/pricing/{card_id}?listing_type=auction&period=all
     → response has raw{} and graded[] grouped by company → grade → records[].

We keep PSA-graded **completed auction sales** (listing_type=auction = real sold
prices, not asking prices) for the **base card** (parallel_id is null, so
Shadowless / 1st-Edition parallels don't contaminate the median), then take the
median per grade.

Header auth: X-API-Key. Free tier ≈ 750 calls/month, so every result is cached
to disk (data/cardsight_cache/) for CACHE_TTL_DAYS to avoid burning quota.

Docs: https://cardsight.ai/documentation/api-reference
"""
import json
import os
import re
import statistics
import time

import requests

CARDSIGHT_BASE_URL = "https://api.cardsight.ai/v1"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cardsight_cache")
CACHE_TTL_DAYS = 7          # price results
ID_CACHE_TTL_DAYS = 90      # card_id resolution is stable — cache it long

# Free tier is ~750 calls/month, so we spend at most TWO calls per uncached card
# (one catalog/search to resolve the UUID, one pricing/{id}) and cache both.


def _api_key() -> str:
    return (os.environ.get("CARDSIGHT_API_KEY", "")
            or os.environ.get("CARDSIGHTAI_API_KEY", ""))


def _cache_path(key: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", key)
    return os.path.join(CACHE_DIR, f"{safe}.json")


def _read_cache(key: str, ttl_days: int = CACHE_TTL_DAYS) -> dict | None:
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
        if time.time() - blob.get("_ts", 0) > ttl_days * 86400:
            return None
        return blob.get("data")
    except Exception:
        return None


def _write_cache(key: str, data: dict) -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(key), "w", encoding="utf-8") as f:
            json.dump({"_ts": time.time(), "data": data}, f)
    except Exception:
        pass


def _norm_num(n) -> str:
    """Normalize a collector number for comparison: '004' -> '4'."""
    m = re.match(r"\s*0*(\d+)", str(n or ""))
    return m.group(1) if m else str(n or "").strip().lower()


def _card_year(card_local_id: str | None) -> str | None:
    """
    Exact release year for a local card id (e.g. 'base1-4' -> '1999'), derived
    from the scraper's set mapping + the cached PokéWallet release dates. No
    extra API calls. CardSight's catalog search needs an exact year to reliably
    surface a specific vintage printing.
    """
    if not card_local_id:
        return None
    try:
        try:
            from scraper import _api_set_id_for, _get_pokewallet_sets
        except Exception:
            from src.scraper import _api_set_id_for, _get_pokewallet_sets
        sid = _api_set_id_for(card_local_id)
        if not sid:
            return None
        for s in _get_pokewallet_sets():
            if str(s.get("set_id")) == str(sid):
                m = re.search(r"(19|20)\d{2}", str(s.get("release_date", "")))
                return m.group(0) if m else None
    except Exception:
        return None
    return None


def _get(session: requests.Session, path: str, params: dict) -> tuple[int, dict | None]:
    try:
        r = session.get(f"{CARDSIGHT_BASE_URL}{path}", params=params, timeout=25)
    except Exception:
        return 0, None
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, None


def _score_candidate(r: dict, name_l: str, set_l: str) -> int:
    """Rank a catalog/search hit by name-exactness and set/release overlap."""
    s = 0
    cname = str(r.get("name", "")).lower()
    if cname == name_l:
        s += 10
    elif name_l in cname or cname in name_l:
        s += 4
    hay = " ".join(str(r.get(k, "")).lower() for k in ("setName", "releaseName", "manufacturerName"))
    if set_l:
        for tok in set_l.split():
            if len(tok) > 2 and tok in hay:
                s += 3
    s += float(r.get("relevance", 0) or 0)
    return s


def _resolve_card_id(session, card_name, set_name, number, cache_key, card_local_id) -> str | None:
    """
    Resolve the CardSight card UUID with a SINGLE catalog/search call, cached
    separately for ID_CACHE_TTL_DAYS (the mapping is stable). Picks the best
    candidate by name + set overlap; number verification happens later against
    the one pricing call we make.
    """
    id_key = f"id::{cache_key}"
    cached_id = _read_cache(id_key, ID_CACHE_TTL_DAYS)
    if cached_id:
        return cached_id.get("card_id")

    name_l = card_name.lower()
    set_l = (set_name or "").lower()
    # CardSight's catalog search is literal: multi-word queries with number/set
    # return nothing, but bare name + exact year reliably surfaces the printing.
    params = {"q": card_name[:300], "type": "card", "take": 25}
    yr = _card_year(card_local_id)
    if yr:
        params["year"] = yr
    sc, d = _get(session, "/catalog/search", params)
    if sc not in (200, 201) or not isinstance(d, dict):
        return None
    results = [r for r in d.get("results", []) if r.get("id")]
    if not results:
        return None
    best = max(results, key=lambda r: _score_candidate(r, name_l, set_l))
    _write_cache(id_key, {"card_id": best["id"]})
    return best["id"]


def _median_bucket(records: list[dict]) -> dict | None:
    """Median of base-card prices from a grade's records (parallel_id null)."""
    prices = [r["price"] for r in records
              if r.get("price") and not r.get("parallel_id")]
    if not prices:
        return None
    return {"price": round(statistics.median(prices), 2), "count": len(prices)}


def get_graded_prices(
    card_name: str,
    card_local_id: str | None = None,
    set_name: str | None = None,
    number: str | None = None,
    force_refresh: bool = False,
) -> dict:
    """
    Return real PSA 9 / PSA 10 / raw sale medians (completed auctions, base card).

    Success:
      {"source":"cardsight",
       "psa10": {"price":float,"count":int}|None,
       "psa9":  {"price":float,"count":int}|None,
       "raw":   {"price":float,"count":int}|None,
       "as_of": "YYYY-MM-DD"|None, "cached": bool}
    Error: {"error": "no_key"|"api_error"|"no_data", "detail"?: str}
    """
    key = _api_key()
    if not key or key == "your_cardsight_key_here":
        return {"error": "no_key"}

    cache_key = card_local_id or " ".join(filter(None, [card_name, set_name, number]))
    if not force_refresh:
        cached = _read_cache(cache_key)
        if cached is not None:
            if cached.get("empty"):
                return {"error": "no_data"}
            return {**cached, "cached": True}

    session = requests.Session()
    session.headers.update({"X-API-Key": key})

    card_id = _resolve_card_id(session, card_name, set_name, number, cache_key, card_local_id)
    if not card_id:
        return {"error": "no_data"}

    sc, p = _get(session, f"/pricing/{card_id}",
                 {"listing_type": "auction", "period": "all", "limit": 100})
    if sc == 401:
        return {"error": "api_error", "detail": "CardSight rejected the API key (401)."}
    if sc == 429:
        return {"error": "api_error", "detail": "CardSight rate limit / monthly quota reached (429)."}
    if sc not in (200, 201) or not isinstance(p, dict):
        return {"error": "api_error", "detail": f"CardSight returned HTTP {sc}."}

    # Verify we resolved the right card — reject a number mismatch rather than
    # returning a wrong-card price. (Don't cache as empty: the ID cache may just
    # be stale, and we still fall back to estimates.)
    if number:
        got = (p.get("card") or {}).get("number")
        if got is not None and _norm_num(got) != _norm_num(number):
            return {"error": "no_data"}

    psa_grades: dict[str, list[dict]] = {}
    for co in (p.get("graded") or []):
        if str(co.get("company_name", "")).upper() != "PSA":
            continue
        for g in co.get("grades", []):
            psa_grades[str(g.get("grade_value", "")).strip()] = g.get("records", [])

    raw_records = (p.get("raw") or {}).get("records", [])

    def _latest(recs):
        ds = [r.get("date") for r in recs if r.get("date")]
        return max(ds)[:10] if ds else None

    all_recs = raw_records + [r for recs in psa_grades.values() for r in recs]

    out = {
        "source": "cardsight",
        "psa10": _median_bucket(psa_grades.get("10", [])),
        "psa9":  _median_bucket(psa_grades.get("9", [])),
        "raw":   _median_bucket(raw_records),
        "as_of": _latest(all_recs),
        "cached": False,
    }

    if not (out["psa10"] or out["psa9"] or out["raw"]):
        _write_cache(cache_key, {"empty": True})
        return {"error": "no_data"}

    _write_cache(cache_key, out)
    return out


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "Charizard"
    setn = sys.argv[2] if len(sys.argv) > 2 else "Base Set"
    num  = sys.argv[3] if len(sys.argv) > 3 else "4"
    print(json.dumps(get_graded_prices(name, set_name=setn, number=num, force_refresh=True), indent=2))
