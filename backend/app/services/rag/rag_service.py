"""
Main RAG Service
Orchestrates all RAG components for end-to-end functionality
"""

import logging
import time
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.models import (
    RAGDocument, RAGDocumentChunk, RAGQuery, 
    RAGIndexMetadata, DocumentStatus
)
from app.services.rag.config import rag_settings
from app.services.rag.document_processor import document_processor
from app.services.rag.embedding_service import embedding_service
from app.services.rag.vector_store import vector_store_service
from app.services.rag.llm_service import llm_service
from app.services.rag.cache_service import cache_service

logger = logging.getLogger(__name__)


class RAGService:
    """Main RAG service orchestrating all components"""
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all RAG components"""
        try:
            logger.info("Initializing RAG system...")
            
            # Initialize cache
            cache_ok = await cache_service.initialize()
            if not cache_ok:
                logger.warning("Redis cache initialization failed, continuing without cache")
            
            # Initialize embedding service
            embed_ok = await embedding_service.initialize()
            if not embed_ok:
                raise RuntimeError("Failed to initialize embedding service")
            
            # Initialize LLM service
            llm_ok = await llm_service.initialize()
            if not llm_ok:
                raise RuntimeError("Failed to initialize LLM service")
            
            # Initialize vector store
            vector_ok = vector_store_service.initialize()
            if not vector_ok:
                raise RuntimeError("Failed to initialize vector store")
            
            self._initialized = True
            logger.info("RAG system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            self._initialized = False
            return False
    
    async def shutdown(self):
        """Shutdown RAG system"""
        await cache_service.close()
        vector_store_service.save_index()
        logger.info("RAG system shutdown complete")
    
    async def upload_document(
        self,
        file_path: str,
        filename: str,
        db: Session,
        user_id: Optional[str] = None
    ) -> RAGDocument:
        """Upload and process a document"""

        if not self._initialized:
            raise RuntimeError("RAG system not initialized")

        start_time = time.time()

        try:
            # Validate file
            validation = document_processor.validate_file(file_path)
            if not validation["valid"]:
                raise ValueError(validation["error"])

            # Calculate file hash
            file_hash = document_processor.calculate_file_hash(file_path)

            # Check if document already exists
            existing = db.query(RAGDocument).filter(
                RAGDocument.document_hash == file_hash
            ).first()

            if existing:
                logger.info(f"Document {filename} already exists (hash: {file_hash})")
                return existing

            # Create document record
            doc = RAGDocument(
                filename=filename,
                original_filename=filename,
                file_path=file_path,
                file_size=Path(file_path).stat().st_size,
                file_type=validation["file_type"],
                document_hash=file_hash,
                status=DocumentStatus.PROCESSING,
                uploaded_by=user_id,
                embedding_model=rag_settings.OLLAMA_EMBEDDING_MODEL
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            try:
                # Process document with proper metadata
                logger.info(f"Processing document: {filename}")
                result = await document_processor.process_document(
                    file_path,
                    metadata={
                        "document_id": doc.id,
                        "filename": filename
                    }
                )

                if result["status"] != "success":
                    raise Exception(result.get("error", "Processing failed"))

                chunks = result["chunks"]
                logger.info(f"Document processed into {len(chunks)} chunks")

                if not chunks:
                    raise ValueError("No chunks were created from the document")

                # Validate chunk metadata
                for i, chunk in enumerate(chunks):
                    if "metadata" not in chunk:
                        chunk["metadata"] = {}
                    
                    # Ensure required fields
                    chunk["metadata"]["document_id"] = doc.id
                    chunk["metadata"]["filename"] = filename
                    chunk["metadata"]["chunk_index"] = i
                    
                    logger.debug(f"Chunk {i} metadata: {chunk['metadata']}")

                # Generate embeddings
                chunk_texts = [chunk["text"] for chunk in chunks]
                logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")

                embeddings = await embedding_service.get_embeddings_batch(
                    chunk_texts,
                    use_cache=True
                )

                if not embeddings:
                    raise RuntimeError("Failed to generate embeddings")

                logger.info(f"Generated {len(embeddings)} embeddings successfully")

                # Prepare metadata for vector store
                chunk_metadatas = [chunk["metadata"] for chunk in chunks]

                # Add to vector store
                logger.info(f"Adding {len(embeddings)} embeddings to vector store...")
                
                vector_ids = await vector_store_service.add_embeddings(
                    embeddings,
                    chunk_texts,
                    chunk_metadatas
                )

                if not vector_ids:
                    raise RuntimeError("No vector IDs returned from add_embeddings")

                logger.info(f"Successfully added {len(vector_ids)} vectors to store")
                logger.info(f"Vector store now has {vector_store_service.faiss_index.ntotal} total vectors")

                # Verify vectors were persisted
                if vector_store_service.faiss_index.ntotal == 0:
                    raise RuntimeError("CRITICAL: Vectors not persisted in FAISS index!")

                # Save chunks to database
                for i, (chunk, vector_id) in enumerate(zip(chunks, vector_ids)):
                    chunk_hash = hashlib.sha256(chunk["text"].encode()).hexdigest()

                    db_chunk = RAGDocumentChunk(
                        document_id=doc.id,
                        chunk_text=chunk["text"],
                        chunk_index=i,
                        chunk_hash=chunk_hash,
                        page_number=chunk["metadata"].get("page_number"),
                        token_count=chunk["metadata"]["token_count"],
                        vector_id=vector_id,
                        embedding_cached=True
                    )
                    db.add(db_chunk)

                # Update document status
                doc.status = DocumentStatus.INDEXED
                doc.chunk_count = len(chunks)
                doc.total_tokens = result["total_tokens"]
                doc.processing_time_seconds = time.time() - start_time
                doc.indexed_at = datetime.now()
                doc.index_name = "main_index"

                db.commit()
                db.refresh(doc)

                logger.info(
                    f"Document {filename} indexed successfully: "
                    f"{len(chunks)} chunks, {vector_store_service.faiss_index.ntotal} total vectors"
                )

                return doc

            except Exception as e:
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                db.commit()
                logger.error(f"Failed to process document: {e}", exc_info=True)
                raise
                
        except Exception as e:
            logger.error(f"Error uploading document {filename}: {e}", exc_info=True)
            raise
    
    async def query(
        self,
        query_text: str,
        db: Session,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        document_ids: Optional[List[int]] = None,
        use_cache: bool = True,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query the RAG system"""

        if not self._initialized:
            raise RuntimeError("RAG system not initialized")

        start_time = time.time()

        try:
            logger.info(f"Processing query: '{query_text[:100]}...'")
            logger.info(f"Parameters: top_k={top_k}, threshold={similarity_threshold}")

            # Check cache
            cache_key = {
                "top_k": top_k,
                "threshold": similarity_threshold,
                "document_ids": document_ids
            }

            if use_cache and rag_settings.ENABLE_CACHE:
                cached_result = await cache_service.get_query_result(query_text, cache_key)
                if cached_result:
                    logger.info("Cache hit for query")
                    if rag_settings.ENABLE_QUERY_LOGGING:
                        self._log_query(db, query_text, cached_result, cache_hit=True, user_id=user_id)
                    return cached_result

            # Generate query embedding
            retrieval_start = time.time()
            logger.info("Generating query embedding...")
            query_embedding = await embedding_service.get_query_embedding(query_text)
            
            # Check vector store
            vector_count = vector_store_service.faiss_index.ntotal
            logger.info(f"Vector store has {vector_count} vectors")

            if vector_count == 0:
                logger.warning("Vector store is empty!")
                return {
                    "query": query_text,
                    "response": "No documents have been indexed yet. Please upload documents first.",
                    "sources": [],
                    "retrieval_time_ms": 0,
                    "generation_time_ms": 0,
                    "total_time_ms": 0,
                    "chunks_retrieved": 0,
                    "cache_hit": False,
                    "confidence_score": None
                }

            # Search vector store with proper threshold
            logger.info(f"Searching with top_k={top_k}, threshold={similarity_threshold}...")
            search_results = await vector_store_service.search(
                query_embedding,
                top_k=top_k,
                threshold=similarity_threshold
            )

            logger.info(f"Search returned {len(search_results)} results")

            # Filter by document_ids if specified
            if document_ids:
                filtered_results = []
                for r in search_results:
                    meta = r.get("metadata", {})
                    
                    # Resolve ID for matching
                    doc_id = None
                    
                    # 1. Try explicit kb_id
                    if meta.get("kb_id"):
                        try: doc_id = int(meta.get("kb_id"))
                        except: pass
                    
                    # 2. Try raw ID clean up
                    if doc_id is None:
                        raw = meta.get("document_id")
                        if isinstance(raw, int):
                            doc_id = raw
                        elif isinstance(raw, str) and raw.startswith("kb_"):
                            try: doc_id = int(raw.replace("kb_", ""))
                            except: pass
                        elif raw is not None:
                            try: doc_id = int(raw)
                            except: pass
                            
                    if doc_id is not None and doc_id in document_ids:
                        filtered_results.append(r)
                        
                search_results = filtered_results
                logger.info(f"After document_id filtering: {len(search_results)} results")

            retrieval_time = (time.time() - retrieval_start) * 1000

            # If no results, return early
            if not search_results:
                logger.warning("No relevant chunks found")
                return {
                    "query": query_text,
                    "response": "No relevant information found in the indexed documents. Try lowering the similarity threshold or rephrasing your query.",
                    "sources": [],
                    "retrieval_time_ms": retrieval_time,
                    "generation_time_ms": 0,
                    "total_time_ms": retrieval_time,
                    "chunks_retrieved": 0,
                    "cache_hit": False,
                    "confidence_score": None
                }

            # Generate response
            generation_start = time.time()
            logger.info(f"Generating response using {len(search_results)} chunks...")
            llm_response = await llm_service.generate_response(
                query_text,
                search_results
            )
            generation_time = (time.time() - generation_start) * 1000

            # Build sources with proper structure
            sources = []
            for result in search_results:
                metadata = result.get("metadata", {})
                
                # Resolve document ID to integer
                doc_id = 0
                raw_id = metadata.get("document_id")
                
                # 1. Prefer explicit kb_id
                if metadata.get("kb_id"):
                    try:
                        doc_id = int(metadata.get("kb_id"))
                    except (ValueError, TypeError):
                        pass
                # 2. Handle string IDs (e.g. "kb_123")
                elif isinstance(raw_id, str) and raw_id.startswith("kb_"):
                    try:
                        doc_id = int(raw_id.replace("kb_", ""))
                    except (ValueError, TypeError):
                        pass
                # 3. Handle standard integer IDs
                elif raw_id is not None:
                    try:
                        doc_id = int(raw_id)
                    except (ValueError, TypeError):
                        pass

                sources.append({
                    "document_id": doc_id,
                    "filename": metadata.get("filename") or metadata.get("title", "unknown"),
                    "chunk_index": metadata.get("chunk_index", 0),
                    "page_number": metadata.get("page_number"),
                    "relevance_score": result["similarity_score"],
                    "excerpt": result["text"][:200] + "..." if len(result["text"]) > 200 else result["text"]
                })

            total_time = (time.time() - start_time) * 1000

            response = {
                "query": query_text,
                "response": llm_response["response"],
                "sources": sources,
                "retrieval_time_ms": retrieval_time,
                "generation_time_ms": generation_time,
                "total_time_ms": total_time,
                "chunks_retrieved": len(search_results),
                "cache_hit": False,
                "confidence_score": llm_response.get("confidence_score")
            }

            logger.info(f"Query completed: {len(search_results)} chunks, {total_time:.2f}ms total")

            # Cache result
            if use_cache and rag_settings.ENABLE_CACHE:
                await cache_service.set_query_result(query_text, cache_key, response)

            # Log query
            if rag_settings.ENABLE_QUERY_LOGGING:
                self._log_query(db, query_text, response, cache_hit=False, user_id=user_id)

            return response

        except Exception as e:
            logger.error(f"Error querying RAG system: {e}", exc_info=True)
            raise
    
    def _log_query(
        self,
        db: Session,
        query_text: str,
        response: Dict[str, Any],
        cache_hit: bool,
        user_id: Optional[str] = None
    ):
        """Log query to database"""
        try:
            query_hash = hashlib.sha256(query_text.encode()).hexdigest()
            
            query_log = RAGQuery(
                query_text=query_text,
                query_hash=query_hash,
                response_text=response["response"],
                response_sources=response.get("sources", []),
                retrieval_time_ms=response.get("retrieval_time_ms", 0),
                generation_time_ms=response.get("generation_time_ms", 0),
                total_time_ms=response.get("total_time_ms", 0),
                chunks_retrieved=response.get("chunks_retrieved", 0),
                cache_hit=cache_hit,
                user_id=user_id
            )
            
            db.add(query_log)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to log query: {e}")
    
    async def delete_document(self, document_id: int, db: Session) -> bool:
        """Delete a document and its embeddings"""
        try:
            doc = db.query(RAGDocument).filter(RAGDocument.id == document_id).first()
            if not doc:
                return False
            
            # Delete vectors
            await vector_store_service.delete_by_document_id(document_id)
            
            # Delete chunks
            db.query(RAGDocumentChunk).filter(
                RAGDocumentChunk.document_id == document_id
            ).delete()
            
            # Delete document
            db.delete(doc)
            db.commit()
            
            # Delete file
            if Path(doc.file_path).exists():
                Path(doc.file_path).unlink()
            
            logger.info(f"Deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    async def reindex_documents(
        self,
        db: Session,
        document_ids: Optional[List[int]] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Reindex documents"""
        
        start_time = time.time()
        
        try:
            query = db.query(RAGDocument)
            
            if document_ids:
                query = query.filter(RAGDocument.id.in_(document_ids))
            elif not force:
                query = query.filter(RAGDocument.status != DocumentStatus.INDEXED)
            
            documents = query.all()
            
            if not documents:
                return {
                    "status": "success",
                    "documents_processed": 0,
                    "message": "No documents to reindex"
                }
            
            processed = 0
            chunks_created = 0
            vectors_indexed = 0
            errors = []
            
            for doc in documents:
                try:
                    updated_doc = await self.upload_document(
                        doc.file_path,
                        doc.filename,
                        db,
                        user_id=doc.uploaded_by
                    )
                    
                    processed += 1
                    chunks_created += updated_doc.chunk_count
                    vectors_indexed += updated_doc.chunk_count
                    
                except Exception as e:
                    errors.append(f"Document {doc.id}: {str(e)}")
                    logger.error(f"Error reindexing document {doc.id}: {e}")
            
            duration = time.time() - start_time
            
            return {
                "status": "success" if not errors else "partial",
                "documents_processed": processed,
                "chunks_created": chunks_created,
                "vectors_indexed": vectors_indexed,
                "duration_seconds": duration,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error in reindex operation: {e}")
            raise
    
    async def get_health(self, db: Session) -> Dict[str, Any]:
        """Get RAG system health status"""

        ollama_available = await llm_service.is_available()
        redis_available = cache_service._initialized

        doc_count = db.query(RAGDocument).filter(
            RAGDocument.status == DocumentStatus.INDEXED
        ).count()

        vector_stats = vector_store_service.get_stats()
        total_vectors = vector_stats.get("total_vectors", 0)

        return {
            "status": "healthy" if self._initialized and total_vectors > 0 else "degraded",
            "ollama_available": ollama_available,
            "redis_available": redis_available,
            "faiss_available": vector_store_service._initialized,
            "index_loaded": total_vectors > 0,
            "total_documents": doc_count,
            "total_vectors": total_vectors,
            "last_query_time": None
        }


# Global RAG service instance
rag_service = RAGService()