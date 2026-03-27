# DeepScan AI API

## Base URL
`http://localhost:8000`

## POST /analyze
### Request
```json
{
  "type": "text | url | image | video",
  "content": "..."
}
```

### Response
```json
{
  "verdict": "Reliable | Doubtful | Fake",
  "score": 0.0,
  "language": "en | fr",
  "explanation": "...",
  "modules": {
    "nlp": {"score": 0.0, "explanation": "...", "signals": {}, "applicable": true},
    "source": {"score": 0.0, "explanation": "...", "signals": {}, "applicable": true},
    "fact_check": {"score": 0.0, "explanation": "...", "signals": {}, "applicable": true},
    "image": {"score": 0.0, "explanation": "...", "signals": {}, "applicable": true},
    "deepfake": {"score": 0.0, "explanation": "...", "signals": {}, "applicable": true}
  }
}
```

## Notes
- Responses are optimized to return within 3 seconds.
- Image/video inputs are mock-processed for the MVP.
- Bilingual support is automatic via language detection.
