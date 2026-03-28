import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs

try:
    import whois
except Exception:
    whois = None

SUSPICIOUS_KEYWORDS = {
    "free", "giveaway", "click", "viral", "buzz", "breaking", "news", "urgent", "hot", "xxx"
}
URL_SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "is.gd"}
IP_REGEX = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
RISKY_PATH_TOKENS = {"login", "verify", "update", "redirect", "secure", "account"}

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
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    return domain


def whois_age_days(domain: str):
    if whois is None:
        return None
    try:
        record = whois.whois(domain)
    except Exception:
        return None

    created = record.creation_date
    if isinstance(created, list):
        created = created[0]
    if not created:
        return None

    if isinstance(created, str):
        try:
            created = datetime.fromisoformat(created)
        except Exception:
            return None

    return max(0, (datetime.utcnow() - created).days)


def score_source(url: str, lang: str):
    if not url.startswith("http"):
        return 0.5, "Non applicable pour ce type d'entrée." if lang == "fr" else "Not applicable for this input type.", {"reason": "not_url"}, False

    domain = domain_from_url(url)
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query or "")
    param_count = len(query_params.keys())
    url_length = len(url)
    has_at = "@" in url
    path_tokens = set(re.findall(r"[a-zA-Z]+", parsed.path.lower()))
    risky_path = bool(path_tokens & RISKY_PATH_TOKENS)

    trusted = set(load_json("domains_trusted.json", []))
    suspicious = set(load_json("domains_suspicious.json", []))
    rankings = load_json("press_rankings.json", {})

    has_https = parsed.scheme == "https"
    suspicious_hits = [k for k in SUSPICIOUS_KEYWORDS if k in domain]
    is_shortener = domain in URL_SHORTENERS
    has_ip = bool(IP_REGEX.match(domain))
    has_punycode = "xn--" in domain
    hyphen_count = domain.count("-")
    digit_count = sum(c.isdigit() for c in domain)

    # Deterministic scoring model
    base_score = 0.5
    bonuses = []
    penalties = []

    if has_https:
        bonuses.append(("https", 0.1))
    else:
        penalties.append(("no_https", 0.1))

    if domain in trusted:
        bonuses.append(("trusted_domain", 0.2))
    if domain in suspicious:
        penalties.append(("suspicious_domain", 0.2))

    if suspicious_hits:
        penalties.append(("suspicious_keywords", min(0.2, 0.05 * len(suspicious_hits))))
    if is_shortener:
        penalties.append(("url_shortener", 0.12))
    if has_ip:
        penalties.append(("ip_domain", 0.2))
    if has_punycode:
        penalties.append(("punycode", 0.15))
    if hyphen_count >= 2:
        penalties.append(("many_hyphens", 0.05))
    if digit_count >= 3:
        penalties.append(("many_digits", 0.05))
    if url_length > 90:
        penalties.append(("long_url", 0.05))
    if param_count >= 3:
        penalties.append(("many_params", 0.05))
    if has_at:
        penalties.append(("at_symbol", 0.1))
    if risky_path:
        penalties.append(("risky_path_tokens", 0.05))

    rank_score = 0.0
    for country, entries in rankings.items():
        for entry in entries:
            if entry.get("domain") == domain:
                rank_score = max(rank_score, float(entry.get("score", 0.0)))

    if rank_score > 0:
        bonuses.append(("press_rank", min(0.2, rank_score)))

    whois_enabled = os.getenv("ENABLE_WHOIS", "false").lower() == "true"
    age_days = None
    if whois_enabled:
        age_days = whois_age_days(domain)
        if age_days is not None:
            if age_days < 90:
                penalties.append(("whois_new_domain", 0.15))
            elif age_days < 365:
                penalties.append(("whois_young_domain", 0.08))
            else:
                bonuses.append(("whois_mature_domain", 0.05))

    bonus_total = sum(b for _, b in bonuses)
    penalty_total = sum(p for _, p in penalties)
    score = round(min(1.0, max(0.0, base_score + bonus_total - penalty_total)), 3)

    explanation = (
        "Source score is computed from HTTPS, reputation lists, URL patterns, press ranking, and WHOIS (optional)."
        if lang == "en"
        else "Le score source est calculé via HTTPS, réputation, motifs d'URL, classement presse et WHOIS (optionnel)."
    )

    signals = {
        "domain": domain,
        "https": has_https,
        "suspicious_keywords": suspicious_hits,
        "shortener": is_shortener,
        "ip_domain": has_ip,
        "punycode": has_punycode,
        "hyphen_count": hyphen_count,
        "digit_count": digit_count,
        "url_length": url_length,
        "param_count": param_count,
        "risky_path": risky_path,
        "has_at_symbol": has_at,
        "reputation": {
            "trusted": domain in trusted,
            "suspicious": domain in suspicious,
            "press_rank_score": rank_score,
        },
        "whois": {
            "enabled": whois_enabled,
            "age_days": age_days,
        },
        "score_breakdown": {
            "base": base_score,
            "bonuses": bonuses,
            "penalties": penalties,
            "bonus_total": round(bonus_total, 3),
            "penalty_total": round(penalty_total, 3),
        },
    }

    return score, explanation, signals, True
