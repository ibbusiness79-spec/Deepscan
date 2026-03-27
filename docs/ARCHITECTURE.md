# DeepScan AI Architecture

## Modules
- NLP Analysis: uses OpenAI or offline HuggingFace (with heuristic fallback) to detect emotional manipulation, clickbait, and bias.
- Source Analysis: checks HTTPS, suspicious patterns, reputation lists, local press ranking score, and optional WHOIS domain age.
- Fact-Check (simulated): searches a mock database of known claims.
- Computer Vision (mock): simulates metadata and manipulation checks.
- Deepfake Detection (mock): simulates blink and facial anomaly checks.

## Scoring
Final score = 0.4 * NLP + 0.3 * Source + 0.3 * Others (average of fact-check, image, deepfake).

## Explainability
Each module provides a plain-language explanation and the signals used for scoring.
