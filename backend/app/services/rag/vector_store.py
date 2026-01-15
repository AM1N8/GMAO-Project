"""
FAISS Vector Store Service for RAG
Handles vector indexing and similarity search
"""

import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

import faiss
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.faiss import FaissVectorStore

from app.services.rag.config import rag_settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """FAISS-based vector store for RAG system"""
    
    def __init__(self):
        self.dimension = rag_settings.FAISS_DIMENSION
        self.index_path = Path(rag_settings.FAISS_INDEX_PATH)
        self.index_name = "main_index"
        
        self.faiss_index: Optional[faiss.Index] = None
        self.vector_store: Optional[FaissVectorStore] = None
        self.storage_context: Optional[StorageContext] = None
        self.index: Optional[VectorStoreIndex] = None
        
        self._initialized = False
        self._metadata_store: Dict[int, Dict[str, Any]] = {}  # Changed to int keys
        self._next_id = 0
    
    def initialize(self) -> bool:
        """Initialize or load FAISS index"""
        try:
            self.index_path.mkdir(parents=True, exist_ok=True)

            index_file = self.index_path / f"{self.index_name}.index"
            metadata_file = self.index_path / f"{self.index_name}.metadata"

            # Check if valid index file exists
            index_exists = index_file.exists() and index_file.stat().st_size > 0

            if index_exists:
                logger.info(f"Loading existing FAISS index from {index_file}")
                try:
                    self.faiss_index = faiss.read_index(str(index_file))
                    logger.info(f"Successfully loaded FAISS index with {self.faiss_index.ntotal} vectors")

                    # Load metadata
                    if metadata_file.exists() and metadata_file.stat().st_size > 0:
                        with open(metadata_file, 'rb') as f:
                            loaded_metadata = pickle.load(f)
                            # Convert string keys back to int if needed
                            self._metadata_store = {
                                int(k) if isinstance(k, str) else k: v 
                                for k, v in loaded_metadata.items()
                            }
                            self._next_id = max(self._metadata_store.keys()) + 1 if self._metadata_store else 0
                        logger.info(f"Loaded {len(self._metadata_store)} metadata entries")
                    else:
                        logger.warning("Metadata file not found or empty")
                        self._metadata_store = {}
                        self._next_id = 0

                except Exception as e:
                    logger.warning(f"Failed to load existing index: {e}. Creating new index.")
                    self._create_new_index()
            else:
                logger.info("No existing index found. Creating new FAISS index")
                self._create_new_index()

            # Initialize LlamaIndex components
            self.vector_store = FaissVectorStore(faiss_index=self.faiss_index)
            self.storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )

            self._initialized = True
            logger.info(f"Vector store initialized. Current vectors: {self.faiss_index.ntotal}")

            return True

        except Exception as e:
            logger.error(f"Error initializing vector store: {e}", exc_info=True)
            self._initialized = False
            return False
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        index_type = rag_settings.FAISS_INDEX_TYPE.lower()
        
        if index_type == "flat":
            self.faiss_index = faiss.IndexFlatL2(self.dimension)
        elif index_type == "ivf":
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.faiss_index = faiss.IndexIVFFlat(
                quantizer, 
                self.dimension, 
                rag_settings.FAISS_NLIST
            )
        elif index_type == "hnsw":
            self.faiss_index = faiss.IndexHNSWFlat(self.dimension, 32)
        else:
            raise ValueError(f"Unknown index type: {index_type}")
        
        self._metadata_store = {}
        self._next_id = 0
        logger.info(f"Created new {index_type.upper()} FAISS index")
    
    def save_index(self) -> bool:
        """Save FAISS index to disk"""
        if not self._initialized or self.faiss_index is None:
            logger.warning("Cannot save index: not initialized")
            return False

        try:
            self.index_path.mkdir(parents=True, exist_ok=True)

            index_file = self.index_path / f"{self.index_name}.index"
            metadata_file = self.index_path / f"{self.index_name}.metadata"

            logger.info(f"Saving index with {self.faiss_index.ntotal} vectors")

            # Save FAISS index
            faiss.write_index(self.faiss_index, str(index_file))

            # Save metadata
            with open(metadata_file, 'wb') as f:
                pickle.dump(self._metadata_store, f)

            logger.info(f"Index saved: {index_file.stat().st_size} bytes, Metadata: {metadata_file.stat().st_size} bytes")
            return True

        except Exception as e:
            logger.error(f"Error saving index: {e}", exc_info=True)
            return False
    
    async def add_embeddings(
        self,
        embeddings: List[np.ndarray],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """Add embeddings to the index"""
        if not self._initialized:
            raise RuntimeError("Vector store not initialized")

        if not embeddings or len(embeddings) == 0:
            logger.warning("No embeddings provided")
            return []

        try:
            # Convert to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)

            # Validate shape
            if len(embeddings_array.shape) != 2:
                raise ValueError(f"Embeddings must be 2D array, got shape {embeddings_array.shape}")

            if embeddings_array.shape[1] != self.dimension:
                raise ValueError(f"Embedding dimension mismatch: got {embeddings_array.shape[1]}, expected {self.dimension}")

            logger.info(f"Adding {len(embeddings)} embeddings. Shape: {embeddings_array.shape}")

            # Train IVF index if needed
            if isinstance(self.faiss_index, faiss.IndexIVFFlat):
                if not self.faiss_index.is_trained:
                    if len(embeddings_array) < self.faiss_index.nlist:
                        logger.warning(f"Not enough vectors for IVF. Switching to Flat index.")
                        self.faiss_index = faiss.IndexFlatL2(self.dimension)
                        self.vector_store = FaissVectorStore(faiss_index=self.faiss_index)
                    else:
                        self.faiss_index.train(embeddings_array)
                        logger.info("IVF index trained")

            # Get starting ID
            start_id = self._next_id
            
            # Add to FAISS
            self.faiss_index.add(embeddings_array)
            
            # Verify addition
            new_total = self.faiss_index.ntotal
            logger.info(f"Added vectors. New total: {new_total}")

            if new_total <= start_id:
                raise RuntimeError("Failed to add vectors to FAISS index")

            # Store metadata with integer IDs
            vector_ids = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                vec_id = start_id + i
                vector_ids.append(str(vec_id))  # Return as string for API compatibility

                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                
                # Ensure critical fields are present
                self._metadata_store[vec_id] = {
                    "text": text,
                    "metadata": metadata,
                    "faiss_index": vec_id
                }

            self._next_id = start_id + len(embeddings)
            
            logger.info(f"Stored {len(vector_ids)} metadata entries. Total: {len(self._metadata_store)}")

            # Save immediately
            save_success = self.save_index()
            if not save_success:
                logger.error("Failed to save index")

            return vector_ids

        except Exception as e:
            logger.error(f"Error adding embeddings: {e}", exc_info=True)
            raise
    
    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        if not self._initialized:
            raise RuntimeError("Vector store not initialized")

        if self.faiss_index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []

        try:
            # Ensure 2D array
            if len(query_embedding.shape) == 1:
                query_array = np.array([query_embedding], dtype=np.float32)
            else:
                query_array = np.array(query_embedding, dtype=np.float32)

            logger.info(f"Searching {self.faiss_index.ntotal} vectors with top_k={top_k}")

            # Set nprobe for IVF
            if isinstance(self.faiss_index, faiss.IndexIVFFlat):
                self.faiss_index.nprobe = rag_settings.FAISS_NPROBE

            # Search FAISS
            distances, indices = self.faiss_index.search(query_array, top_k)

            logger.info(f"Raw distances: {distances[0]}")
            logger.info(f"Raw indices: {indices[0]}")

            # Process results
            results = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx == -1:
                    continue
                
                # Convert L2 distance to normalized similarity score
                # L2 distance range: [0, infinity), lower is better
                # Normalize: similarity = 1 / (1 + sqrt(distance))
                # This gives values in (0, 1] where 1 is perfect match
                normalized_distance = float(np.sqrt(distance))
                similarity = 1.0 / (1.0 + normalized_distance)
                
                logger.debug(f"idx={idx}, L2_dist={distance:.2f}, norm_dist={normalized_distance:.2f}, sim={similarity:.4f}")

                # Apply threshold on similarity (0-1 scale)
                if threshold is not None and similarity < threshold:
                    logger.debug(f"Filtered: similarity {similarity:.4f} < threshold {threshold}")
                    continue
                
                # Get metadata
                idx_int = int(idx)
                metadata_entry = self._metadata_store.get(idx_int, {})

                if not metadata_entry:
                    logger.warning(f"No metadata for index {idx_int}")
                    continue
                
                text = metadata_entry.get("text", "")
                metadata = metadata_entry.get("metadata", {})

                if not text:
                    logger.warning(f"Empty text for index {idx_int}")
                    continue
                
                # Build result with all required fields
                result = {
                    "vector_id": str(idx_int),
                    "text": text,
                    "metadata": {
                        "document_id": metadata.get("document_id"),
                        "filename": metadata.get("filename", "unknown"),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "page_number": metadata.get("page_number"),
                        **metadata  # Include all other metadata
                    },
                    "distance": float(distance),
                    "similarity_score": float(similarity),
                    "index": idx_int
                }

                results.append(result)

            logger.info(f"Returning {len(results)} results after filtering")
            return results

        except Exception as e:
            logger.error(f"Error searching index: {e}", exc_info=True)
            raise
    
    async def delete_by_document_id(self, document_id: int) -> int:
        """Delete all vectors for a document"""
        if not self._initialized:
            return 0
        
        try:
            ids_to_delete = []
            for vec_id, data in self._metadata_store.items():
                if data.get("metadata", {}).get("document_id") == document_id:
                    ids_to_delete.append(vec_id)
            
            for vec_id in ids_to_delete:
                del self._metadata_store[vec_id]
            
            logger.info(f"Removed {len(ids_to_delete)} vectors from document {document_id}")
            return len(ids_to_delete)
            
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
            return 0
    
    async def rebuild_index(self) -> bool:
        """Rebuild index from scratch"""
        try:
            valid_data = list(self._metadata_store.values())
            
            if not valid_data:
                logger.info("No data to rebuild")
                return True
            
            self._create_new_index()
            logger.info(f"Rebuilding index with {len(valid_data)} vectors...")
            
            self.save_index()
            logger.info("Index rebuilt successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        index_file = self.index_path / f"{self.index_name}.index"
        index_size_mb = index_file.stat().st_size / (1024 * 1024) if index_file.exists() else 0
        
        return {
            "status": "initialized",
            "index_type": type(self.faiss_index).__name__,
            "dimension": self.dimension,
            "total_vectors": self.faiss_index.ntotal if self.faiss_index else 0,
            "metadata_entries": len(self._metadata_store),
            "index_size_mb": round(index_size_mb, 2),
            "is_trained": getattr(self.faiss_index, 'is_trained', True)
        }
    
    def clear_index(self) -> bool:
        """Clear all vectors from index"""
        try:
            self._create_new_index()
            self.save_index()
            logger.info("Index cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing index: {e}")
            return False


# Global vector store instance
vector_store_service = VectorStoreService()