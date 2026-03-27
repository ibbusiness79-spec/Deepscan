from pydantic import BaseModel, Field
from typing import Dict, Any

class AnalyzeRequest(BaseModel):
    type: str = Field(..., description="text | url | image | video")
    content: str = Field(..., description="Raw text, URL, or base64 content")

class ModuleResult(BaseModel):
    score: float
    explanation: str
    signals: Dict[str, Any]
    applicable: bool = True

class AnalyzeResponse(BaseModel):
    verdict: str
    score: float
    language: str
    explanation: str
    modules: Dict[str, ModuleResult]
