"""
PSA (Professional Sports Authenticator) public API client.

The PSA public API currently exposes a single endpoint — cert verification by
cert number — which returns the real grade and population report for an
already-graded card. It does NOT provide price data, so grading ROI is computed
separately from simulated graded prices in analyzer.py.

Auth: PSA issues a bearer access token from your account. Put it in .env as
PSA_API_KEY; it is sent as the "Authorization: bearer <token>" header.

Docs: https://www.psacard.com/publicapi/documentation
"""
import os

import requests

PSA_BASE_URL = "https://api.psacard.com/publicapi"


def _psa_token() -> str:
    return os.environ.get("PSA_API_KEY", "")


def get_cert(cert_number: str) -> dict:
    """
    Look up a PSA-graded card by its cert number.

    Returns a normalized dict on success, or a dict with an "error" key:
      - "no_key"    — PSA_API_KEY is not configured
      - "not_found" — no cert matches that number
      - "api_error" — network / upstream failure (includes "detail")
    """
    token = _psa_token()
    if not token or token == "your_psa_token_here":
        return {"error": "no_key"}

    cert = str(cert_number).strip()
    if not cert.isdigit():
        return {"error": "not_found"}

    try:
        resp = requests.get(
            f"{PSA_BASE_URL}/cert/GetByCertNumber/{cert}",
            headers={"Authorization": f"bearer {token}"},
            timeout=15,
        )
    except Exception as e:
        return {"error": "api_error", "detail": str(e)}

    if resp.status_code == 401:
        return {"error": "api_error", "detail": "PSA rejected the API key (401)."}
    if resp.status_code == 429:
        return {"error": "api_error", "detail": "PSA rate limit reached (429). Free keys allow 100 calls/day."}
    if resp.status_code != 200:
        return {"error": "api_error", "detail": f"PSA returned HTTP {resp.status_code}."}

    try:
        data = resp.json()
    except Exception:
        return {"error": "api_error", "detail": "PSA returned an unreadable response."}

    # PSA wraps the payload under "PSACert"
    c = data.get("PSACert") or data
    if not c or not (c.get("CertNumber") or c.get("SpecID")):
        return {"error": "not_found"}

    return {
        "cert_number":       c.get("CertNumber"),
        "spec_id":           c.get("SpecID"),
        "year":              c.get("Year"),
        "brand":             c.get("Brand"),
        "category":          c.get("Category"),
        "subject":           c.get("Subject"),
        "card_number":       c.get("CardNumber"),
        "variety":           c.get("Variety"),
        "grade":             c.get("CardGrade"),
        "grade_description": c.get("GradeDescription"),
        "total_population":  c.get("TotalPopulation"),
        "population_higher": c.get("PopulationHigher"),
        "is_dual_cert":      c.get("IsDualCert"),
        "is_psadna":         c.get("IsPSADNA"),
    }


if __name__ == "__main__":
    import sys
    cn = sys.argv[1] if len(sys.argv) > 1 else "00000000"
    print(get_cert(cn))
