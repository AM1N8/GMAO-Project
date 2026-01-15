
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnowledgeBaseDocument
from app.schemas import (
    KnowledgeBaseDocumentCreate,
    KnowledgeBaseDocumentUpdate,
    KnowledgeBaseDocumentResponse,
    KnowledgeBaseDocumentListResponse
)
from app.services.knowledge_base_service import knowledge_base_service
# Add auth dependency if available, e.g. get_current_user

router = APIRouter()

@router.post("/", response_model=KnowledgeBaseDocumentResponse)
async def create_document(
    doc_in: KnowledgeBaseDocumentCreate,
    db: Session = Depends(get_db)
):
    """Create a new knowledge base document"""
    return await knowledge_base_service.create_document(db, doc_in)

@router.get("/", response_model=KnowledgeBaseDocumentListResponse)
def list_documents(
    page: int = 1,
    size: int = 20,
    category: Optional[str] = None,
    type_panne: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List documents with pagination and filtering"""
    skip = (page - 1) * size
    return knowledge_base_service.list_documents(
        db, skip=skip, limit=size, 
        category=category, type_panne=type_panne, search=search
    )

@router.get("/{doc_id}", response_model=KnowledgeBaseDocumentResponse)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific document by ID"""
    doc = db.query(KnowledgeBaseDocument).filter(
        KnowledgeBaseDocument.id == doc_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.put("/{doc_id}", response_model=KnowledgeBaseDocumentResponse)
async def update_document(
    doc_id: int,
    doc_in: KnowledgeBaseDocumentUpdate,
    db: Session = Depends(get_db)
):
    """Update a document and re-index it"""
    doc = await knowledge_base_service.update_document(db, doc_id, doc_in)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """Delete a document"""
    success = await knowledge_base_service.delete_document(db, doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "success", "message": "Document deleted"}

@router.post("/{doc_id}/reindex", response_model=KnowledgeBaseDocumentResponse)
async def reindex_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """Force re-indexing of a document"""
    # Simply calling update with no changes triggers re-index logic or we can add a specific method
    # reusing update without changes for simplicity
    doc = await knowledge_base_service.update_document(db, doc_id, KnowledgeBaseDocumentUpdate())
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
