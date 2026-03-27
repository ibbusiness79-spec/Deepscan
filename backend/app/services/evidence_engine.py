import os
import re
from functools import lru_cache
from typing import Dict, Any, Tuple, List
from urllib.parse import urlparse

import requests
import json

SERPAPI_ENDPOINT = "https://serpapi.com/search"
DEFAULT_BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"

STOPWORDS = {
    "en": {"the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "have", "has", "will", "been", "their", "there", "about", "into"},
    "fr": {"les", "des", "une", "pour", "avec", "dans", "sur", "est", "sont", "été", "avoir", "cela", "ceci", "comme", "mais", "plus", "tout", "tous"},
}

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


def extract_query(text: str, lang: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    tokens = re.findall(r"[\w\-']+", text.lower())
    tokens = [t for t in tokens if len(t) > 3 and t not in STOPWORDS.get(lang, set())]
    if not tokens:
        return text[:160]
    return " ".join(tokens[:12])


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


def _get_timeout() -> float:
    return float(os.getenv("EVIDENCE_TIMEOUT", "2.5"))


def _get_count() -> int:
    return int(os.getenv("EVIDENCE_COUNT", "5"))


@lru_cache(maxsize=256)
def _bing_search(query: str, lang: str) -> Dict[str, Any]:
    api_key = os.getenv("BING_API_KEY") or os.getenv("SEARCH_API_KEY")
    if not api_key:
        return {"error": "missing_key"}

    endpoint = os.getenv("BING_ENDPOINT", DEFAULT_BING_ENDPOINT)

    params = {
        "q": query,
        "count": _get_count(),
        "responseFilter": "Webpages",
        "setLang": "fr" if lang == "fr" else "en",
        "safeSearch": "Moderate",
    }
    headers = {"Ocp-Apim-Subscription-Key": api_key}

    resp = requests.get(endpoint, params=params, headers=headers, timeout=_get_timeout())
    resp.raise_for_status()
    return resp.json()


@lru_cache(maxsize=256)
def _serpapi_search(query: str, lang: str) -> Dict[str, Any]:
    api_key = os.getenv("SERPAPI_API_KEY") or os.getenv("SEARCH_API_KEY")
    if not api_key:
        return {"error": "missing_key"}

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "hl": "fr" if lang == "fr" else "en",
        "num": _get_count(),
    }
    resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=_get_timeout())
    resp.raise_for_status()
    return resp.json()


def _extract_results(provider: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = []
    if provider == "bing":
        items = (data.get("webPages") or {}).get("value", []) or []
        for item in items:
            results.append({
                "title": item.get("name"),
                "url": item.get("url"),
                "snippet": item.get("snippet"),
            })
    elif provider == "serpapi":
        items = data.get("organic_results", []) or []
        for item in items:
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
            })
    return results


def score_evidence(text: str, lang: str) -> Tuple[float, str, Dict[str, Any]]:
    provider = os.getenv("EVIDENCE_PROVIDER", "bing").lower()
    if provider not in {"bing", "serpapi"}:
        return 0.55, TRANSLATIONS[lang]["no_key"], {"status": "disabled", "provider": provider}

    query = extract_query(text, lang)

    try:
        data = _bing_search(query, lang) if provider == "bing" else _serpapi_search(query, lang)
    except Exception as exc:
        return 0.55, TRANSLATIONS[lang]["no_results"], {"status": "error", "error": str(exc), "provider": provider}

    if data.get("error") == "missing_key":
        return 0.55, TRANSLATIONS[lang]["no_key"], {"status": "missing_key", "provider": provider}

    results = _extract_results(provider, data)
    if not results:
        return 0.55, TRANSLATIONS[lang]["no_results"], {"status": "not_found", "provider": provider}

    trusted = set(load_json("domains_trusted.json", []))
    suspicious = set(load_json("domains_suspicious.json", []))

    matches = []
    trusted_hits = 0
    suspicious_hits = 0

    for item in results[:5]:
        url = item.get("url", "")
        title = item.get("title", "")
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

    score = 0.5
    score += min(0.24, trusted_hits * 0.08)
    score -= min(0.2, suspicious_hits * 0.1)

    unique_domains = len({m["domain"] for m in matches if m.get("domain")})
    if unique_domains >= 2:
        score += 0.05

    score = round(max(0.0, min(1.0, score)), 3)

    signals = {
        "status": "matched",
        "provider": provider,
        "query": query,
        "trusted_hits": trusted_hits,
        "suspicious_hits": suspicious_hits,
        "matches": matches,
    }
    return score, TRANSLATIONS[lang]["found"], signals
