import os
from functools import lru_cache
from typing import Dict, Any, Tuple, List
from urllib.parse import urlparse

import requests
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "..", "..", "data")


def load_json(filename: str, default):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


TRANSLATIONS = {
    "en": {
        "no_key": "Web evidence API key missing; evidence search skipped.",
        "no_results": "No web evidence found for this claim.",
        "found": "Web evidence found from public sources.",
    },
    "fr": {
        "no_key": "Clé API de recherche web manquante; evidence ignorée.",
        "no_results": "Aucune preuve web trouvée pour cette affirmation.",
        "found": "Des preuves web ont été trouvées dans des sources publiques.",
    },
}


@lru_cache(maxsize=256)
def _bing_search(query: str, lang: str) -> Dict[str, Any]:
    api_key = os.getenv("BING_API_KEY")
    if not api_key:
        return {"error": "missing_key"}

    endpoint = os.getenv("BING_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search")
    timeout = float(os.getenv("EVIDENCE_TIMEOUT", "2.5"))

    params = {
        "q": query,
        "count": int(os.getenv("EVIDENCE_COUNT", "5")),
        "responseFilter": "Webpages",
        "setLang": "fr" if lang == "fr" else "en",
        "safeSearch": "Moderate",
    }
    headers = {"Ocp-Apim-Subscription-Key": api_key}

    resp = requests.get(endpoint, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def score_evidence(text: str, lang: str) -> Tuple[float, str, Dict[str, Any]]:
    provider = os.getenv("EVIDENCE_PROVIDER", "bing").lower()
    if provider != "bing":
        return 0.55, TRANSLATIONS[lang]["no_key"], {"status": "disabled", "provider": provider}

    query = text.strip()
    if len(query) > 200:
        query = query[:200]

    try:
        data = _bing_search(query, lang)
    except Exception as exc:
        return 0.55, TRANSLATIONS[lang]["no_results"], {"status": "error", "error": str(exc)}

    if data.get("error") == "missing_key":
        return 0.55, TRANSLATIONS[lang]["no_key"], {"status": "missing_key", "provider": "bing"}

    results: List[Dict[str, Any]] = (data.get("webPages") or {}).get("value", []) or []
    if not results:
        return 0.55, TRANSLATIONS[lang]["no_results"], {"status": "not_found", "provider": "bing"}

    trusted = set(load_json("domains_trusted.json", []))
    suspicious = set(load_json("domains_suspicious.json", []))

    matches = []
    trusted_hits = 0
    suspicious_hits = 0

    for item in results[:5]:
        url = item.get("url", "")
        title = item.get("name", "")
        snippet = item.get("snippet", "")
        domain = domain_from_url(url)
        if domain in trusted:
            trusted_hits += 1
        if domain in suspicious:
            suspicious_hits += 1
        matches.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "domain": domain,
        })

    # Evidence scoring: more trusted sources => higher score
    score = 0.5
    score += min(0.24, trusted_hits * 0.08)
    score -= min(0.2, suspicious_hits * 0.1)

    unique_domains = len({m["domain"] for m in matches if m.get("domain")})
    if unique_domains >= 2:
        score += 0.05

    score = round(max(0.0, min(1.0, score)), 3)

    signals = {
        "status": "matched",
        "provider": "bing",
        "trusted_hits": trusted_hits,
        "suspicious_hits": suspicious_hits,
        "matches": matches,
    }
    return score, TRANSLATIONS[lang]["found"], signals
