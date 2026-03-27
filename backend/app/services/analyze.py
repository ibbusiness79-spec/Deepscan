import re
from urllib.parse import urlparse
from app.services.schemas import AnalyzeRequest

EMOTIONAL_WORDS = {
    "shocking", "outrage", "panic", "anger", "hate", "amazing", "incroyable", "choquant",
    "scandale", "honte", "terreur", "urgent", "breaking", "révélation", "catastrophe"
}
CLICKBAIT_PATTERNS = [
    r"you won't believe", r"what happens next", r"shocking truth", r"incroyable", r"à couper le souffle",
    r"ne ratez pas", r"cliquez ici", r"vous ne devinerez jamais"
]
BIAS_WORDS = {"always", "never", "everyone", "nobody", "tous", "personne", "jamais"}
SUSPICIOUS_DOMAIN_KEYWORDS = {"free", "giveaway", "click", "viral", "buzz", "breaking", "news", "urgent"}
CREDIBLE_DOMAINS = {
    "bbc.com", "reuters.com", "apnews.com", "france24.com", "lemonde.fr", "rfi.fr", "afp.com"
}

TRANSLATIONS = {
    "en": {
        "verdict_reliable": "Reliable",
        "verdict_doubtful": "Doubtful",
        "verdict_fake": "Fake",
        "explain_prefix": "Summary",
        "not_applicable": "Not applicable for this input type.",
    },
    "fr": {
        "verdict_reliable": "Fiable",
        "verdict_doubtful": "Douteux",
        "verdict_fake": "Faux",
        "explain_prefix": "Résumé",
        "not_applicable": "Non applicable pour ce type d'entrée.",
    },
}


def detect_language(text: str) -> str:
    text_lower = text.lower()
    if re.search(r"[éèêàçôûîù]", text_lower):
        return "fr"
    french_markers = [" le ", " la ", " les ", " des ", " une ", " un ", " ce ", " cette "]
    english_markers = [" the ", " and ", " is ", " are ", " this ", " that "]
    fr_score = sum(1 for m in french_markers if m in text_lower)
    en_score = sum(1 for m in english_markers if m in text_lower)
    return "fr" if fr_score >= en_score else "en"


def score_nlp(text: str, lang: str):
    text_lower = text.lower()
    emotional_hits = [w for w in EMOTIONAL_WORDS if w in text_lower]
    clickbait_hits = [p for p in CLICKBAIT_PATTERNS if re.search(p, text_lower)]
    bias_hits = [w for w in BIAS_WORDS if w in text_lower]

    risk = 0.0
    risk += min(0.4, 0.1 * len(emotional_hits))
    risk += min(0.4, 0.2 * len(clickbait_hits))
    risk += min(0.2, 0.05 * len(bias_hits))
    risk = min(1.0, risk)
    score = round(1.0 - risk, 3)

    explanation = (
        "Emotional manipulation, clickbait phrases, and absolute language can signal misinformation."
        if lang == "en"
        else "La manipulation émotionnelle, le clickbait et le langage absolu sont des signaux de désinformation."
    )
    signals = {
        "emotional_words": emotional_hits,
        "clickbait_patterns": clickbait_hits,
        "bias_words": bias_hits,
    }
    return score, explanation, signals


def score_source(content: str, lang: str):
    parsed = urlparse(content) if content.startswith("http") else None
    if not parsed:
        return 0.5, TRANSLATIONS[lang]["not_applicable"], {"reason": "not_url"}, False

    domain = parsed.netloc.lower().replace("www.", "")
    has_https = parsed.scheme == "https"
    suspicious_hits = [k for k in SUSPICIOUS_DOMAIN_KEYWORDS if k in domain]
    credible = domain in CREDIBLE_DOMAINS

    risk = 0.0
    if not has_https:
        risk += 0.2
    if suspicious_hits:
        risk += min(0.4, 0.1 * len(suspicious_hits))
    if credible:
        risk -= 0.2
    if len(domain) > 25:
        risk += 0.1

    risk = min(1.0, max(0.0, risk))
    score = round(1.0 - risk, 3)

    explanation = (
        "We check domain credibility, HTTPS security, and suspicious keywords."
        if lang == "en"
        else "Nous vérifions la crédibilité du domaine, HTTPS et les mots-clés suspects."
    )
    signals = {
        "domain": domain,
        "https": has_https,
        "suspicious_keywords": suspicious_hits,
        "credible_domain": credible,
    }
    return score, explanation, signals, True


def score_fact_check(text: str, lang: str):
    text_lower = text.lower()
    simulated_false = ["miracle cure", "secret government", "puce 5g", "vaccin tue"]
    match = next((p for p in simulated_false if p in text_lower), None)

    if match:
        score = 0.2
        explanation = (
            "Simulated fact-check found similar claim rated false."
            if lang == "en"
            else "Vérification simulée: un énoncé similaire est jugé faux."
        )
        signals = {"match": match, "status": "false"}
    else:
        score = 0.6
        explanation = (
            "No matching fact-check found in the simulated database."
            if lang == "en"
            else "Aucun résultat trouvé dans la base simulée de fact-checking."
        )
        signals = {"status": "not_found"}

    return score, explanation, signals


def score_image(content: str, lang: str):
    if not content:
        return 0.5, TRANSLATIONS[lang]["not_applicable"], {"reason": "empty"}, False

    simulated_flags = []
    if "edited" in content.lower() or "photoshop" in content.lower():
        simulated_flags.append("metadata_inconsistency")
    if "deepfake" in content.lower():
        simulated_flags.append("manipulation_artifacts")

    risk = 0.1 * len(simulated_flags)
    score = round(1.0 - min(0.8, risk), 3)

    explanation = (
        "We simulate metadata and manipulation checks for images."
        if lang == "en"
        else "Nous simulons l'analyse des métadonnées et des manipulations d'images."
    )
    signals = {"flags": simulated_flags}
    return score, explanation, signals, True


def score_deepfake(content: str, lang: str):
    if not content:
        return 0.5, TRANSLATIONS[lang]["not_applicable"], {"reason": "empty"}, False

    simulated_flags = []
    if "blink" in content.lower() or "eye" in content.lower():
        simulated_flags.append("blinking_inconsistency")
    if "face" in content.lower():
        simulated_flags.append("face_anomaly")

    risk = 0.15 * len(simulated_flags)
    score = round(1.0 - min(0.7, risk), 3)

    explanation = (
        "We simulate deepfake checks such as blinking and facial anomalies."
        if lang == "en"
        else "Nous simulons les contrôles deepfake: clignements et anomalies faciales."
    )
    signals = {"flags": simulated_flags}
    return score, explanation, signals, True


def verdict_from_score(score: float, lang: str) -> str:
    if score >= 0.7:
        return TRANSLATIONS[lang]["verdict_reliable"]
    if score >= 0.4:
        return TRANSLATIONS[lang]["verdict_doubtful"]
    return TRANSLATIONS[lang]["verdict_fake"]


def analyze_content(payload: AnalyzeRequest):
    content = payload.content.strip()
    lang = detect_language(content)

    nlp_score, nlp_expl, nlp_signals = score_nlp(content, lang)
    source_score, source_expl, source_signals, source_applicable = score_source(content, lang)
    fact_score, fact_expl, fact_signals = score_fact_check(content, lang)

    image_score, image_expl, image_signals, image_applicable = score_image(
        content if payload.type in {"image", "video"} else "", lang
    )
    deepfake_score, deepfake_expl, deepfake_signals, deepfake_applicable = score_deepfake(
        content if payload.type == "video" else "", lang
    )

    weights = {
        "nlp": 0.4,
        "source": 0.3,
        "others": 0.3,
    }

    others_avg = round((fact_score + image_score + deepfake_score) / 3, 3)
    final_score = round(
        nlp_score * weights["nlp"] + source_score * weights["source"] + others_avg * weights["others"],
        3,
    )

    verdict = verdict_from_score(final_score, lang)

    explanation = (
        f"{TRANSLATIONS[lang]['explain_prefix']}: score={final_score}, verdict={verdict}. "
        "Signals from NLP, source, and media checks were combined with weighted rules."
        if lang == "en"
        else f"{TRANSLATIONS[lang]['explain_prefix']} : score={final_score}, verdict={verdict}. "
        "Les signaux NLP, source et médias sont combinés par pondération."
    )

    return {
        "verdict": verdict,
        "score": final_score,
        "language": lang,
        "explanation": explanation,
        "modules": {
            "nlp": {
                "score": nlp_score,
                "explanation": nlp_expl,
                "signals": nlp_signals,
                "applicable": True,
            },
            "source": {
                "score": source_score,
                "explanation": source_expl,
                "signals": source_signals,
                "applicable": source_applicable,
            },
            "fact_check": {
                "score": fact_score,
                "explanation": fact_expl,
                "signals": fact_signals,
                "applicable": True,
            },
            "image": {
                "score": image_score,
                "explanation": image_expl,
                "signals": image_signals,
                "applicable": image_applicable,
            },
            "deepfake": {
                "score": deepfake_score,
                "explanation": deepfake_expl,
                "signals": deepfake_signals,
                "applicable": deepfake_applicable,
            },
        },
    }
