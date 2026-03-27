# DeepScan AI

**Tagline:** See the truth. Share with confidence.

DeepScan AI is a lightweight, bilingual (FR/EN) platform that detects fake news, deepfakes, and misinformation from text, URLs, and media inputs. It is optimized for low-bandwidth, mobile-first environments.

## What’s Included
- FastAPI backend with modular AI analysis
- React + Tailwind frontend
- Explainable scoring pipeline
- Sample dataset and demo script

## Project Structure
```
backend/
  app/
frontend/
  src/
  index.html
  package.json
docs/
  API.md
  ARCHITECTURE.md
data/
  samples.json
demo/
  demo.py
```

## Backend Setup
```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## API Quick Test
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"type":"text","content":"BREAKING: You won\'t believe this miracle cure."}'
```

## Demo Script
```bash
python demo/demo.py
```

## Sample Inputs
See `data/samples.json` for curated fake and real news examples.

## Expected Outputs (Sample)
- Fake inputs should return a low score (below 0.4) and verdict "Fake" / "Faux".
- Neutral or factual inputs should return higher scores and "Reliable" / "Fiable".

## Notes
- Image/video analysis is simulated for the MVP, but interfaces are ready for real models.
- The system is designed to respond in under 3 seconds.
