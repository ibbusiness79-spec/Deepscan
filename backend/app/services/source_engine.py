import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse

try:
    import whois
except Exception:
    whois = None

SUSPICIOUS_KEYWORDS = {
    "free", "giveaway", "click", "viral", "buzz", "breaking", "news", "urgent", "hot", "xxx"
}
URL_SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "is.gd"}
IP_REGEX = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

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

    risk = 0.0
    if not has_https:
        risk += 0.2
    if suspicious_hits:
        risk += min(0.3, 0.05 * len(suspicious_hits))
    if is_shortener:
        risk += 0.15
    if has_ip:
        risk += 0.25
    if has_punycode:
        risk += 0.2
    if hyphen_count >= 2:
        risk += 0.1
    if digit_count >= 3:
        risk += 0.1

    reputation_bonus = 0.0
    if domain in trusted:
        reputation_bonus += 0.2
    if domain in suspicious:
        risk += 0.2

    rank_score = 0.0
    for country, entries in rankings.items():
        for entry in entries:
            if entry.get("domain") == domain:
                rank_score = max(rank_score, float(entry.get("score", 0.0)))

    reputation_bonus += min(0.2, rank_score)

    whois_enabled = os.getenv("ENABLE_WHOIS", "false").lower() == "true"
    age_days = None
    if whois_enabled:
        age_days = whois_age_days(domain)
        if age_days is not None:
            if age_days < 90:
                risk += 0.2
            elif age_days < 365:
                risk += 0.1
            else:
                reputation_bonus += 0.05

    risk = min(1.0, max(0.0, risk - reputation_bonus))
    score = round(1.0 - risk, 3)

    explanation = (
        "We check HTTPS, suspicious patterns, reputation lists, press rankings, and optional WHOIS age."
        if lang == "en"
        else "Nous vérifions HTTPS, signaux suspects, réputation, classement presse et l'âge WHOIS (optionnel)."
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
        "reputation": {
            "trusted": domain in trusted,
            "suspicious": domain in suspicious,
            "press_rank_score": rank_score,
        },
        "whois": {
            "enabled": whois_enabled,
            "age_days": age_days,
        },
    }

    return score, explanation, signals, True
