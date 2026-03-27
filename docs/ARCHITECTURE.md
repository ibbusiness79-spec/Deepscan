# DeepScan AI Architecture

## Modules
- NLP Analysis: detects emotional manipulation, clickbait, and bias.
- Source Analysis: checks domain credibility, HTTPS, suspicious keywords.
- Fact-Check (simulated): searches a mock database of known claims.
- Computer Vision (mock): simulates metadata and manipulation checks.
- Deepfake Detection (mock): simulates blink and facial anomaly checks.

## Scoring
Final score = 0.4 * NLP + 0.3 * Source + 0.3 * Others (average of fact-check, image, deepfake).

## Explainability
Each module provides a plain-language explanation and the signals used for scoring.
