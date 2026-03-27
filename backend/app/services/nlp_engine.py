import json
import os
import re
from typing import Dict, Any, Tuple

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from transformers import pipeline
except Exception:
    pipeline = None

EMOTIONAL_WORDS = {
    "shocking", "outrage", "panic", "anger", "hate", "amazing", "incroyable", "choquant",
    "scandale", "honte", "terreur", "urgent", "breaking", "révélation", "catastrophe"
}
CLICKBAIT_PATTERNS = [
    r"you won't believe", r"what happens next", r"shocking truth", r"incroyable", r"à couper le souffle",
    r"ne ratez pas", r"cliquez ici", r"vous ne devinerez jamais"
]
BIAS_WORDS = {"always", "never", "everyone", "nobody", "tous", "personne", "jamais"}

TRANSLATIONS = {
    "en": {
        "explain_rules": "Heuristic signals: emotional language, clickbait phrasing, and absolute claims.",
        "explain_openai": "LLM analysis combined with heuristic signals for explainability.",
        "explain_hf": "Offline transformer sentiment intensity combined with heuristic signals.",
    },
    "fr": {
        "explain_rules": "Signaux heuristiques : langage émotionnel, clickbait et affirmations absolues.",
        "explain_openai": "Analyse LLM combinée avec des signaux heuristiques pour l'explicabilité.",
        "explain_hf": "Analyse locale (transformer) combinée avec des signaux heuristiques.",
    },
}


def heuristic_signals(text: str) -> Tuple[float, Dict[str, Any]]:
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

    signals = {
        "emotional_words": emotional_hits,
        "clickbait_patterns": clickbait_hits,
        "bias_words": bias_hits,
    }
    return score, signals


def try_openai(text: str, lang: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI()

    prompt = (
        "You are an NLP module for misinformation detection. "
        "Analyze the text for emotional manipulation, clickbait, and linguistic bias. "
        "Return JSON only with keys: score_nlp (0-1, higher = more reliable), "
        "explanation (simple, short, in the target language), "
        "emotional_words (array), clickbait_phrases (array), bias_words (array). "
        f"Target language: {lang}. Text: {text}"
    )

    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.2,
        max_output_tokens=220,
    )

    raw = getattr(response, "output_text", "") or ""
    json_text = extract_json(raw)
    if not json_text:
        return None

    try:
        data = json.loads(json_text)
    except Exception:
        return None

    score = float(data.get("score_nlp", 0.5))
    explanation = str(data.get("explanation", ""))
    signals = {
        "emotional_words": data.get("emotional_words", []),
        "clickbait_patterns": data.get("clickbait_phrases", []),
        "bias_words": data.get("bias_words", []),
        "provider": "openai",
        "model": model,
    }
    return round(max(0.0, min(1.0, score)), 3), explanation, signals


def try_hf(text: str):
    if pipeline is None:
        return None

    model_name = os.getenv("HF_SENTIMENT_MODEL", "nlptown/bert-base-multilingual-uncased-sentiment")
    try:
        classifier = pipeline("sentiment-analysis", model=model_name)
        result = classifier(text[:512])
    except Exception:
        return None

    if not result:
        return None

    label = result[0].get("label", "")
    score = float(result[0].get("score", 0.5))
    stars = 3
    match = re.search(r"(\d)", label)
    if match:
        stars = int(match.group(1))

    sentiment_risk = abs(stars - 3) / 2.0
    return {
        "sentiment_stars": stars,
        "sentiment_score": round(score, 3),
        "sentiment_risk": round(sentiment_risk, 3),
        "model": model_name,
    }


def extract_json(text: str) -> str:
    if not text:
        return ""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start : end + 1]


def analyze_nlp(text: str, lang: str):
    provider = os.getenv("NLP_PROVIDER", "auto").lower()

    # OpenAI path
    if provider in {"auto", "openai"}:
        openai_result = try_openai(text, lang)
        if openai_result:
            score, explanation, signals = openai_result
            return score, explanation, signals

    # Offline HF path
    if provider in {"auto", "hf"}:
        heur_score, heur_signals = heuristic_signals(text)
        hf = try_hf(text)
        if hf:
            score = round(max(0.0, min(1.0, heur_score - 0.2 * hf["sentiment_risk"])), 3)
            explanation = TRANSLATIONS[lang]["explain_hf"]
            signals = {**heur_signals, **hf, "provider": "huggingface"}
            return score, explanation, signals

    # Final fallback: heuristics only
    score, signals = heuristic_signals(text)
    explanation = TRANSLATIONS[lang]["explain_rules"]
    signals["provider"] = "heuristic"
    return score, explanation, signals
