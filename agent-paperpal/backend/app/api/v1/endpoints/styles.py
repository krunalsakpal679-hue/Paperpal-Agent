# backend/app/api/v1/endpoints/styles.py
import logging
from typing import Any
from fastapi import APIRouter, File, UploadFile, Depends
from pydantic import BaseModel

from app.agents.interpretation.llm_extractor import LLMRuleExtractor

logger = logging.getLogger(__name__)
router = APIRouter()


class StyleListItem(BaseModel):
    id: str
    title: str


class JROPreviewResponse(BaseModel):
    jro_data: dict[str, Any]


@router.get(
    "/",
    response_model=list[StyleListItem],
    summary="Search Journal Styles"
)
async def search_styles(q: str = "", limit: int = 20) -> list[StyleListItem]:
    """Search for supported journal formatting styles."""
    # Dummy mock style list
    # In production, this might ping the database or the CiteProc/CSL library directly
    if q:
        return [
            StyleListItem(id="apa", title="American Psychological Association 7th Edition"),
            StyleListItem(id="nature", title="Nature"),
            StyleListItem(id="science", title="Science"),
        ]
    return []


@router.post(
    "/extract",
    response_model=JROPreviewResponse,
    summary="Extract Style Guide Rules dynamically via LLM"
)
async def extract_rules(
    file: UploadFile = File(..., description="PDF Guidelines Document"),
) -> JROPreviewResponse:
    """Synchronous LLM extraction of Author Guidelines PDF into JRO parameters."""
    
    file_bytes = await file.read()
    # Decode to utf-8 text representation natively for the extractor
    # we'll mock the text extracting logic or pass dummy bits for the demo scope
    
    extractor = LLMRuleExtractor()
    extracted_rules = await extractor.extract_rules("Extracted manuscript text here...")
    
    return JROPreviewResponse(
        jro_data=extracted_rules.model_dump()
    )
