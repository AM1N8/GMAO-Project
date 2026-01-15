"""
RAG API Router
Endpoints for document upload, querying, and management
"""

import logging
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models import RAGDocument, RAGQuery as RAGQueryModel, DocumentStatus
from app.schemas import (
    RAGQueryRequest, RAGQueryResponse, RAGDocumentUploadResponse,
    RAGDocumentResponse, RAGDocumentListResponse, RAGIndexStatsResponse,
    RAGReindexRequest, RAGReindexResponse, RAGCacheClearResponse,
    RAGHealthResponse,
    # V2 schemas
    RAGQueryRequestV2, RAGQueryResponseV2, RAGCitationV2,
    RAGRoutingInfo, RAGGraphContext
)
from app.services.rag.rag_service import rag_service
from app.services.rag.cache_service import cache_service
from app.services.rag.vector_store import vector_store_service
from app.services.rag.config import rag_settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== DOCUMENT ENDPOINTS ====================

@router.post("/documents/upload", response_model=RAGDocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Upload a document for RAG indexing
    
    Supported formats: PDF, DOCX, TXT, MD, CSV
    """
    
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()[1:]
        if file_extension not in rag_settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_extension}' not allowed. Allowed: {rag_settings.ALLOWED_FILE_TYPES}"
            )
        
        # Save uploaded file
        upload_dir = Path(rag_settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process document
        doc = await rag_service.upload_document(
            str(file_path),
            file.filename,
            db,
            user_id=user_id
        )
        
        return RAGDocumentUploadResponse(
            document_id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size,
            file_type=doc.file_type,
            status=doc.status,
            message=f"Document uploaded and {'indexed' if doc.status == DocumentStatus.INDEXED else 'processing'} successfully"
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=RAGDocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[DocumentStatus] = None,
    db: Session = Depends(get_db)
):
    """
    List all documents with pagination
    
    Filter by status if specified
    """
    
    query = db.query(RAGDocument)
    
    if status:
        query = query.filter(RAGDocument.status == status)
    
    total = query.count()
    documents = query.order_by(desc(RAGDocument.created_at)).offset(skip).limit(limit).all()
    
    return RAGDocumentListResponse(
        total=total,
        documents=[RAGDocumentResponse.model_validate(doc) for doc in documents],
        skip=skip,
        limit=limit
    )


@router.get("/documents/{document_id}", response_model=RAGDocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get details of a specific document"""
    
    doc = db.query(RAGDocument).filter(RAGDocument.id == document_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return RAGDocumentResponse.model_validate(doc)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Delete a document and its embeddings"""
    
    success = await rag_service.delete_document(document_id, db)
    
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": f"Document {document_id} deleted successfully"}


# ==================== QUERY ENDPOINTS ====================

@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    request: RAGQueryRequest,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Query the RAG system
    
    Returns AI-generated response with source documents
    """
    
    try:
        result = await rag_service.query(
            query_text=request.query,
            db=db,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            document_ids=request.document_ids,
            use_cache=request.use_cache,
            user_id=user_id
        )
        
        # Filter sources if not requested
        if not request.include_sources:
            result["sources"] = []
        
        return RAGQueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error querying RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/v2", response_model=RAGQueryResponseV2)
async def query_rag_v2(
    request: RAGQueryRequestV2,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Enhanced RAG query (V2) with:
    - Confidence-aware query routing
    - Hierarchical document retrieval
    - Graph context enrichment
    - Structured citations
    - KPI integration
    """
    import time
    
    start_time = time.time()
    
    try:
        # Initialize new components (lazy import to avoid startup issues)
        from app.services.rag.router.query_router import query_router
        from app.services.rag.router.intent_classifier import IntentType
        from app.services.rag.kpi.kpi_executor import kpi_executor
        from app.services.rag.config import rag_settings
        
        # 1. Route the query
        route_start = time.time()
        route_decision = await query_router.route(request.query, db)
        routing_time_ms = (time.time() - route_start) * 1000
        
        # Build routing info for response
        routing_info = RAGRoutingInfo(
            request_id=route_decision.request_id,
            primary_handler=route_decision.primary_handler,
            handlers_used=route_decision.handlers,
            intent=route_decision.intent.value,
            confidence=route_decision.confidence,
            reasoning=route_decision.reasoning,
            kpi_detected=route_decision.kpi_type,
            equipment_mentioned=route_decision.entities.equipment_names
        ) if request.include_routing else None
        
        # 2. Execute based on routing decision
        retrieval_start = time.time()
        kpi_data = None
        citations = []
        response_text = ""
        chunks_retrieved = 0
        
        # SQL path for KPI queries (or if KPI detected in hybrid)
        if route_decision.kpi_type and (route_decision.primary_handler == "sql" or route_decision.intent == IntentType.HYBRID):
            kpi_result = await kpi_executor.execute(
                route_decision.kpi_type,
                route_decision.entities,
                db,
                query_text=request.query
            )
            kpi_data = kpi_result.data if kpi_result.success else None
            
            # Generate response from KPI data if it exists
            if kpi_result.success and kpi_result.formatted_context:
                response_text = kpi_result.formatted_context
            
        # Document/Graph/Hybrid paths - only proceed if no KPI response yet or if it's hybrid
        if not response_text or route_decision.intent == IntentType.HYBRID:
            # Use the existing rag_service with scoped documents from graph
            scoped_doc_ids = route_decision.scoped_document_ids or request.document_ids
            
            result = await rag_service.query(
                query_text=request.query,
                db=db,
                top_k=request.top_k,
                similarity_threshold=request.similarity_threshold,
                document_ids=scoped_doc_ids,
                use_cache=request.use_cache,
                user_id=user_id
            )
            
            response_text = result.get("response", "")
            chunks_retrieved = result.get("chunks_retrieved", 0)
            
            # Convert sources to V2 citations
            if request.include_sources:
                for source in result.get("sources", []):
                    # Safely handle document_id conversion (in case of cached string IDs)
                    raw_id = source.get("document_id", 0)
                    doc_id = 0
                    try:
                        if isinstance(raw_id, int):
                            doc_id = raw_id
                        elif isinstance(raw_id, str):
                            # Handle "kb_" prefix or numeric strings
                            clean_id = raw_id.replace("kb_", "") if raw_id.startswith("kb_") else raw_id
                            doc_id = int(clean_id)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert document_id '{raw_id}' to int, defaulting to 0")
                        doc_id = 0

                    excerpt_text = source.get("excerpt", "")[:200]
                    score_val = source.get("relevance_score", 0.0)
                    
                    citations.append(RAGCitationV2(
                        document_name=source.get("filename", "Unknown"),
                        document_id=doc_id,
                        section_title=source.get("section_title"),
                        page_number=source.get("page_number"),
                        excerpt=excerpt_text,
                        relevance_score=score_val,
                        # Compatibility fields for frontend
                        text=excerpt_text,
                        score=score_val,
                        formatted=f"[{source.get('filename', 'Unknown')}"
                                  f"{' - ' + source.get('section_title') if source.get('section_title') else ''}"
                                  f"{' (p.' + str(source.get('page_number')) + ')' if source.get('page_number') else ''}]"
                    ))
        
        retrieval_time_ms = (time.time() - retrieval_start) * 1000
        
        # 3. Build graph context if available
        graph_context = None
        graph_time_ms = 0.0
        
        if request.include_graph_context and route_decision.graph_context:
            graph_start = time.time()
            gc = route_decision.graph_context
            graph_context = RAGGraphContext(
                related_equipment=gc.equipment_context,
                failure_chains=gc.failure_chains[:5],  # Limit for response size
                causal_chains=gc.causal_chains[:5],
                summary=gc.summary
            )
            graph_time_ms = (time.time() - graph_start) * 1000
        
        total_time_ms = (time.time() - start_time) * 1000
        
        return RAGQueryResponseV2(
            query=request.query,
            response=response_text,
            citations=citations,
            routing=routing_info,
            graph_context=graph_context,
            kpi_data=kpi_data,
            routing_time_ms=round(routing_time_ms, 2),
            retrieval_time_ms=round(retrieval_time_ms, 2),
            graph_time_ms=round(graph_time_ms, 2),
            generation_time_ms=0.0,  # Included in retrieval for now
            total_time_ms=round(total_time_ms, 2),
            chunks_retrieved=chunks_retrieved,
            cache_hit=False,
            provider_used=rag_settings.PRIMARY_LLM_PROVIDER
        )
        
    except Exception as e:
        logger.error(f"Error in RAG v2 query: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/queries", response_model=List[dict])
async def get_query_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get query history"""
    
    query = db.query(RAGQueryModel)
    
    if user_id:
        query = query.filter(RAGQueryModel.user_id == user_id)
    
    queries = query.order_by(desc(RAGQueryModel.created_at)).offset(skip).limit(limit).all()
    
    return [
        {
            "id": q.id,
            "query": q.query_text,
            "response": q.response_text[:200] + "..." if len(q.response_text) > 200 else q.response_text,
            "cache_hit": q.cache_hit,
            "total_time_ms": q.total_time_ms,
            "created_at": q.created_at
        }
        for q in queries
    ]


# ==================== INDEX MANAGEMENT ====================

@router.get("/index/stats", response_model=RAGIndexStatsResponse)
async def get_index_stats(db: Session = Depends(get_db)):
    """Get statistics about the RAG index"""
    
    vector_stats = vector_store_service.get_stats()
    
    doc_count = db.query(RAGDocument).filter(
        RAGDocument.status == DocumentStatus.INDEXED
    ).count()
    
    chunk_count = db.query(func.sum(RAGDocument.chunk_count)).scalar() or 0
    
    latest_doc = db.query(RAGDocument).filter(
        RAGDocument.status == DocumentStatus.INDEXED
    ).order_by(desc(RAGDocument.indexed_at)).first()
    
    return RAGIndexStatsResponse(
        index_name="main_index",
        total_documents=doc_count,
        total_chunks=int(chunk_count),
        total_vectors=vector_stats.get("total_vectors", 0),
        embedding_model=rag_settings.OLLAMA_EMBEDDING_MODEL,
        dimension=rag_settings.FAISS_DIMENSION,
        index_size_mb=vector_stats.get("index_size_mb", 0),
        last_updated=latest_doc.indexed_at if latest_doc else None,
        is_active=vector_stats.get("status") == "initialized"
    )


@router.post("/index/reindex", response_model=RAGReindexResponse)
async def reindex_documents(
    request: RAGReindexRequest,
    db: Session = Depends(get_db)
):
    """
    Reindex documents
    
    Can reindex specific documents or all documents
    """
    
    try:
        result = await rag_service.reindex_documents(
            db=db,
            document_ids=request.document_ids,
            force=request.force
        )
        
        if request.clear_cache:
            await cache_service.clear_all()
        
        return RAGReindexResponse(**result)
        
    except Exception as e:
        logger.error(f"Error reindexing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/rebuild")
async def rebuild_index():
    """
    Rebuild the entire FAISS index
    
    This removes deleted vectors and optimizes the index
    """
    
    try:
        success = await vector_store_service.rebuild_index()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to rebuild index")
        
        return {"message": "Index rebuilt successfully"}
        
    except Exception as e:
        logger.error(f"Error rebuilding index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CACHE MANAGEMENT ====================

@router.post("/cache/clear", response_model=RAGCacheClearResponse)
async def clear_cache(
    cache_type: str = Query("all", pattern="^(embeddings|queries|all)$")
):
    """
    Clear Redis cache
    
    - embeddings: Clear only embedding cache
    - queries: Clear only query results cache
    - all: Clear all cache
    """
    
    try:
        if cache_type == "embeddings":
            keys_deleted = await cache_service.clear_embeddings()
        elif cache_type == "queries":
            keys_deleted = await cache_service.clear_queries()
        else:
            keys_deleted = await cache_service.clear_all()
        
        return RAGCacheClearResponse(
            status="success",
            keys_deleted=keys_deleted,
            cache_type=cache_type
        )
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    
    try:
        stats = await cache_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rag/debug/search-test")
async def debug_search_test():
    """Debug endpoint to test vector search directly"""
    try:
        from app.services.rag import vector_store_service, embedding_service
        
        # Get a test query
        test_query = "cahier de charge"
        
        # Generate embedding
        query_embedding = await embedding_service.get_query_embedding(test_query)
        
        # Check index status
        index_info = {
            "total_vectors": vector_store_service.faiss_index.ntotal,
            "metadata_entries": len(vector_store_service._metadata_store),
            "index_type": type(vector_store_service.faiss_index).__name__,
            "dimension": vector_store_service.dimension
        }
        
        # Try search with NO threshold
        results_no_threshold = await vector_store_service.search(
            query_embedding,
            top_k=5,
            threshold=None
        )
        
        # Sample a few metadata entries
        sample_metadata = {}
        for i, (vec_id, data) in enumerate(list(vector_store_service._metadata_store.items())[:3]):
            sample_metadata[vec_id] = {
                "text_preview": data.get("text", "")[:100],
                "metadata": data.get("metadata", {}),
                "index": data.get("index")
            }
        
        return {
            "test_query": test_query,
            "query_embedding_shape": str(query_embedding.shape),
            "index_info": index_info,
            "results_count": len(results_no_threshold),
            "results": results_no_threshold[:3] if results_no_threshold else [],
            "sample_metadata": sample_metadata
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/debug/vector-store-detailed")
async def debug_vector_store_detailed():
    """Detailed vector store debugging"""
    try:
        from app.services.rag.vector_store import vector_store_service
        
        # Check index file details
        index_file = Path(rag_settings.FAISS_INDEX_PATH) / "main_index.index"
        metadata_file = Path(rag_settings.FAISS_INDEX_PATH) / "main_index.metadata"
        
        index_info = {
            "index_file_exists": index_file.exists(),
            "index_file_size": index_file.stat().st_size if index_file.exists() else 0,
            "metadata_file_exists": metadata_file.exists(),
            "metadata_file_size": metadata_file.stat().st_size if metadata_file.exists() else 0,
            "faiss_index_ntotal": vector_store_service.faiss_index.ntotal,
            "metadata_store_size": len(vector_store_service._metadata_store),
            "index_dimension": vector_store_service.dimension,
            "is_initialized": vector_store_service._initialized
        }
        
        # Sample first few metadata entries
        sample_entries = {}
        for i, (vec_id, data) in enumerate(list(vector_store_service._metadata_store.items())[:5]):
            sample_entries[vec_id] = {
                "text_preview": data.get("text", "")[:100],
                "metadata_keys": list(data.get("metadata", {}).keys()),
                "index_position": data.get("index")
            }
        
        return {
            "index_info": index_info,
            "sample_metadata_entries": sample_entries,
            "total_metadata_entries": len(vector_store_service._metadata_store)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.post("/debug/test-embedding-add")
async def debug_test_embedding_add():
    """Test adding embeddings to vector store"""
    try:
        from app.services.rag.embedding_service import embedding_service
        from app.services.rag.vector_store import vector_store_service
        
        # Test texts
        test_texts = [
            "Test document about maintenance procedures",
            "Test document about safety protocols", 
            "Test document about equipment specifications"
        ]
        
        # Generate embeddings
        embeddings = await embedding_service.get_embeddings_batch(test_texts, use_cache=False)
        
        # Check embedding dimensions
        embedding_info = {
            "num_embeddings": len(embeddings),
            "embedding_shape": embeddings[0].shape if embeddings else "No embeddings",
            "embedding_dtype": str(embeddings[0].dtype) if embeddings else "No embeddings"
        }
        
        # Add to vector store
        vector_ids = await vector_store_service.add_embeddings(
            embeddings,
            test_texts,
            [{"source": "debug_test", "doc_id": i} for i in range(len(test_texts))]
        )
        
        # Check results
        result = {
            "embedding_info": embedding_info,
            "vector_ids_returned": len(vector_ids),
            "faiss_index_ntotal_before": "N/A",  # We don't have before state
            "faiss_index_ntotal_after": vector_store_service.faiss_index.ntotal,
            "metadata_entries_after": len(vector_store_service._metadata_store)
        }
        
        # Save index
        save_success = vector_store_service.save_index()
        result["save_success"] = save_success
        
        return result
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ==================== HEALTH & STATUS ====================

@router.get("/health", response_model=RAGHealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check for RAG system
    
    Checks status of all components
    """
    
    try:
        health = await rag_service.get_health(db)
        return RAGHealthResponse(**health)
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))