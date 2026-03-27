from fastapi import APIRouter
from app.services.analyze import analyze_content
from app.services.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest):
    return analyze_content(payload)
