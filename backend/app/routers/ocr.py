from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session
from typing import List

from app.services.ocr_service import ocr_service
from app.database import get_db
from app.models import OcrExtraction
from app.schemas import OcrExtractionCreate, OcrExtractionResponse
import logging

router = APIRouter(
    tags=["OCR (Vision AI)"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/bmp"]

def validate_image(file: UploadFile):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

@router.get("/info", response_class=JSONResponse)
async def get_ocr_info():
    """
    Returns the currently active Vision Language Model (VLM).
    """
    return ocr_service.get_active_model()

@router.post("/markdown", response_class=PlainTextResponse)
async def ocr_to_markdown(file: UploadFile = File(...)):
    """
    **Best for Docs:** detailed Markdown with preserved tables and headers.
    """
    validate_image(file)
    try:
        content = await file.read()
        return await ocr_service.extract_markdown_vlm(content)
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/html", response_class=HTMLResponse)
async def ocr_to_html(file: UploadFile = File(...)):
    """
    **Best for Embedding:** Returns semantic HTML (<table>, <div>) ready to paste.
    """
    validate_image(file)
    try:
        content = await file.read()
        return await ocr_service.extract_semantic_html(content)
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/json", response_class=JSONResponse)
async def ocr_to_json(file: UploadFile = File(...)):
    """
    **Best for Data:** Extracts data as structured JSON (e.g., for forms/invoices).
    """
    validate_image(file)
    try:
        content = await file.read()
        import json
        json_str = await ocr_service.extract_structured_json(content)
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/text", response_class=PlainTextResponse)
async def ocr_to_text(file: UploadFile = File(...)):
    """
    **Best for Search:** Plain text extraction with minimal formatting.
    """
    validate_image(file)
    try:
        content = await file.read()
        return await ocr_service.extract_text(content)
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== PERSISTENT STORAGE ENDPOINTS ====================

@router.post("/extractions", response_model=OcrExtractionResponse)
async def save_ocr_extraction(extraction: OcrExtractionCreate, db: Session = Depends(get_db)):
    """
    Save an OCR extraction result permanently to the database.
    """
    db_extraction = OcrExtraction(**extraction.model_dump())
    db.add(db_extraction)
    db.commit()
    db.refresh(db_extraction)
    return db_extraction

@router.get("/extractions", response_model=List[OcrExtractionResponse])
async def list_ocr_extractions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all permanently saved OCR extractions.
    """
    return db.query(OcrExtraction).order_by(OcrExtraction.created_at.desc()).offset(skip).limit(limit).all()

@router.delete("/extractions/{extraction_id}")
async def delete_ocr_extraction(extraction_id: int, db: Session = Depends(get_db)):
    """
    Delete a saved OCR extraction.
    """
    db_extraction = db.query(OcrExtraction).filter(OcrExtraction.id == extraction_id).first()
    if not db_extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    db.delete(db_extraction)
    db.commit()
    return {"status": "success", "message": "Extraction deleted"}
