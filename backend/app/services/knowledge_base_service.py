
import logging
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import KnowledgeBaseDocument
from app.schemas import (
    KnowledgeBaseDocumentCreate,
    KnowledgeBaseDocumentUpdate,
    KnowledgeBaseDocumentListResponse
)
from app.services.rag.document_processor import document_processor
from app.services.rag.embedding_service import embedding_service
from app.services.rag.vector_store import vector_store_service
from app.services.rag.config import rag_settings

logger = logging.getLogger(__name__)

class KnowledgeBaseService:

    @staticmethod
    async def create_document(db: Session, doc_in: KnowledgeBaseDocumentCreate) -> KnowledgeBaseDocument:
        """Create a new document and index it in RAG"""
        try:
            # 1. Save to DB
            db_doc = KnowledgeBaseDocument(
                title=doc_in.title,
                category=doc_in.category,
                type_panne=doc_in.type_panne,
                content=doc_in.content,
                safety_level=doc_in.safety_level,
                version=1,
                indexed=False
            )
            db.add(db_doc)
            db.commit()
            db.refresh(db_doc)

            # 2. Index in RAG
            await KnowledgeBaseService._index_document(db, db_doc)
            
            return db_doc
        except Exception as e:
            logger.error(f"Error creating KB document: {e}")
            raise

    @staticmethod
    async def update_document(db: Session, doc_id: int, doc_in: KnowledgeBaseDocumentUpdate) -> Optional[KnowledgeBaseDocument]:
        """Update a document, increment version, and re-index"""
        try:
            db_doc = db.query(KnowledgeBaseDocument).filter(KnowledgeBaseDocument.id == doc_id).first()
            if not db_doc:
                return None

            # Update fields
            update_data = doc_in.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_doc, field, value)
            
            # Increment version
            db_doc.version += 1
            db_doc.indexed = False # Reset indexed status until re-indexed
            db.commit()
            db.refresh(db_doc)

            # Re-index (Delete old vectors + Add new)
            # Remove old vectors first
            await vector_store_service.delete_by_document_id(f"kb_{doc_id}")
            
            # Add new
            await KnowledgeBaseService._index_document(db, db_doc)

            return db_doc
        except Exception as e:
            logger.error(f"Error updating KB document {doc_id}: {e}")
            raise

    @staticmethod
    async def delete_document(db: Session, doc_id: int) -> bool:
        """Delete document and remove from RAG index"""
        try:
            db_doc = db.query(KnowledgeBaseDocument).filter(KnowledgeBaseDocument.id == doc_id).first()
            if not db_doc:
                return False

            # Delete from RAG
            await vector_store_service.delete_by_document_id(f"kb_{doc_id}")

            # Delete from DB
            db.delete(db_doc)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting KB document {doc_id}: {e}")
            raise

    @staticmethod
    def list_documents(
        db: Session, 
        skip: int = 0, 
        limit: int = 20,
        category: Optional[str] = None,
        type_panne: Optional[str] = None,
        search: Optional[str] = None
    ) -> dict:
        """List documents with filtering"""
        query = db.query(KnowledgeBaseDocument)

        if category:
            query = query.filter(KnowledgeBaseDocument.category == category)
        if type_panne:
            query = query.filter(KnowledgeBaseDocument.type_panne == type_panne)
        if search:
            query = query.filter(KnowledgeBaseDocument.title.ilike(f"%{search}%"))

        total = query.count()
        items = query.order_by(desc(KnowledgeBaseDocument.updated_at)).offset(skip).limit(limit).all()

        return {
            "items": items,
            "total": total,
            "page": (skip // limit) + 1,
            "size": limit,
            "pages": (total + limit - 1) // limit
        }

    @staticmethod
    async def _index_document(db: Session, doc: KnowledgeBaseDocument):
        """Internal method to index document content into Vector Store"""
        try:
            logger.info(f"Indexing KB document {doc.id}: {doc.title}")
            
            # 1. Chunking
            # We use a mocked 'Document' object structure similar to LlamaIndex to reuse logic or do simple splitting
            # Since we have raw text, we use the sentence splitter from document_processor logic manually
            # or simply rely on langchain/llama_index splitters if imported.
            # Here we reuse the text_splitter instance from document_processor if accessible, or create new.
            
            splitter = document_processor.text_splitter 
            nodes = splitter.split_text(doc.content)
            
            if not nodes:
                logger.warning(f"No content to index for KB doc {doc.id}")
                return

            chunk_texts = nodes
            chunk_metadatas = []
            
            # 2. Prepare Metadata
            for i, text in enumerate(chunk_texts):
                chunk_metadatas.append({
                    "document_id": f"kb_{doc.id}", # Prefix to distinguish from file uploads
                    "source": "knowledge_base",
                    "kb_id": doc.id,
                    "title": doc.title,
                    "filename": doc.title,  # For RAG service compatibility
                    "file_name": doc.title,  # Alias for compatibility
                    "category": doc.category,
                    "type_panne": doc.type_panne or "General",
                    "safety_level": doc.safety_level,
                    "version": doc.version,
                    "chunk_index": i
                })

            # 3. Generate Embeddings
            embeddings = await embedding_service.get_embeddings_batch(chunk_texts, use_cache=True)
            
            # 4. Store Vectors
            if embeddings:
                await vector_store_service.add_embeddings(
                    embeddings=embeddings,
                    texts=chunk_texts,
                    metadatas=chunk_metadatas
                )
                
                # Check persistence
                vector_store_service.save_index()
                
                # Update status
                doc.indexed = True
                db.commit()
                logger.info(f"Successfully indexed KB document {doc.id} with {len(chunk_texts)} chunks.")

        except Exception as e:
            logger.error(f"Failed to index KB document {doc.id}: {e}")
            # Ensure we don't crash the request, but mark indexed=False
            doc.indexed = False
            db.commit()
            # We re-raise to inform the caller if needed, or swallow to allow "soft fail" on indexing
            # For now, we log and swallow to allow DB save to succeed even if RAG fails temporarily
            pass

knowledge_base_service = KnowledgeBaseService()
