import json
import urllib.request

API_URL = "http://localhost:8000/analyze"

samples = [
    {"type": "text", "content": "BREAKING: You won't believe this miracle cure. Secret government lab confirms it works overnight."},
    {"type": "text", "content": "France 24 rapporte un accord régional sur la sécurité alimentaire signé ce matin."},
    {"type": "url", "content": "http://breaking-free-news.example.com/viral-story"},
]

for sample in samples:
    payload = json.dumps(sample).encode("utf-8")
    req = urllib.request.Request(API_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    print("=" * 60)
    print("Input:", sample["content"][:80])
    print("Score:", data["score"], "Verdict:", data["verdict"])
    print("Explanation:", data["explanation"])
