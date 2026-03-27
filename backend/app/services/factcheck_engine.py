import os
import re
from functools import lru_cache
from typing import Dict, Any, Tuple

import requests

FACTCHECK_ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

RATING_MAP = [
    (re.compile(r"(pants on fire|false|faux|fake|incorrect|untrue)", re.I), 0.2),
    (re.compile(r"(mostly false|misleading|partly false|mixed|mixture|partiellement faux)", re.I), 0.4),
    (re.compile(r"(true|correct|accurate|vrai|exact)", re.I), 0.8),
]

TRANSLATIONS = {
    "en": {
        "no_key": "Fact-check API key missing; using simplified fallback.",
        "no_match": "No matching fact-check found from the public database.",
        "match": "Matching fact-check results found in public databases.",
    },
    "fr": {
        "no_key": "Clé API fact-check manquante; fallback simplifié.",
        "no_match": "Aucun fact-check correspondant trouvé dans la base publique.",
        "match": "Des résultats de fact-checking ont été trouvés dans la base publique.",
    },
}


def _rating_to_score(text: str) -> float:
    for pattern, score in RATING_MAP:
        if pattern.search(text or ""):
            return score
    return 0.6


@lru_cache(maxsize=256)
def _fetch_factchecks(query: str, lang: str) -> Dict[str, Any]:
    api_key = os.getenv("FACTCHECK_API_KEY")
    if not api_key:
        return {"error": "missing_key"}

    params = {
        "query": query,
        "languageCode": "fr" if lang == "fr" else "en",
        "pageSize": int(os.getenv("FACTCHECK_PAGE_SIZE", "3")),
        "maxAgeDays": int(os.getenv("FACTCHECK_MAX_AGE_DAYS", "3650")),
        "key": api_key,
    }
    timeout = float(os.getenv("FACTCHECK_TIMEOUT", "2.5"))
    resp = requests.get(FACTCHECK_ENDPOINT, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def score_fact_check(text: str, lang: str) -> Tuple[float, str, Dict[str, Any]]:
    query = text.strip()
    if len(query) > 200:
        query = query[:200]

    try:
        data = _fetch_factchecks(query, lang)
    except Exception as exc:
        return 0.55, TRANSLATIONS[lang]["no_match"], {"status": "error", "error": str(exc)}

    if data.get("error") == "missing_key":
        # Minimal fallback if key is missing
        return 0.55, TRANSLATIONS[lang]["no_key"], {"status": "missing_key"}

    claims = data.get("claims", []) or []
    if not claims:
        return 0.55, TRANSLATIONS[lang]["no_match"], {"status": "not_found"}

    matches = []
    scores = []
    for claim in claims:
        claim_text = claim.get("text", "")
        claim_date = claim.get("claimDate", "")
        reviews = claim.get("claimReview", []) or []
        for review in reviews:
            publisher = (review.get("publisher") or {}).get("name", "")
            url = review.get("url", "")
            rating = review.get("textualRating", "")
            review_date = review.get("reviewDate", "")
            score = _rating_to_score(rating)
            scores.append(score)
            matches.append({
                "claim": claim_text,
                "publisher": publisher,
                "rating": rating,
                "review_date": review_date,
                "claim_date": claim_date,
                "url": url,
                "score": score,
            })

    if not scores:
        return 0.55, TRANSLATIONS[lang]["no_match"], {"status": "not_found"}

    # Conservative: take the minimum (worst) rating
    final_score = round(min(scores), 3)

    return (
        final_score,
        TRANSLATIONS[lang]["match"],
        {
            "status": "matched",
            "matches": matches[:5],
        },
    )
