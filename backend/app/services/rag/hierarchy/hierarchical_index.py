"""
Hierarchical Index
Multi-level FAISS indices for document, section, and chunk retrieval
"""

import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

import faiss

from app.services.rag.config import rag_settings
from app.services.rag.hierarchy.document_hierarchy import (
    DocumentMeta,
    SectionMeta,
    ChunkMeta,
    HierarchicalResult
)

logger = logging.getLogger(__name__)


class HierarchicalIndex:
    """
    Multi-level FAISS indices for hierarchical retrieval.
    
    Maintains three levels:
    1. Document index - document summaries (coarse)
    2. Section index - section summaries (medium)
    3. Chunk index - fine-grained chunks (detailed)
    """
    
    def __init__(
        self,
        dimension: int = 768,
        index_path: Optional[str] = None
    ):
        self.dimension = dimension
        self.index_path = Path(index_path or rag_settings.FAISS_INDEX_PATH) / "hierarchical"
        
        # Level 1: Document index
        self.document_index: Optional[faiss.Index] = None
        self.document_metadata: Dict[int, DocumentMeta] = {}
        self._doc_next_id = 0
        
        # Level 2: Section index  
        self.section_index: Optional[faiss.Index] = None
        self.section_metadata: Dict[int, SectionMeta] = {}
        self.section_texts: Dict[int, str] = {}  # Section summaries
        self._section_next_id = 0
        
        # Level 3: Chunk index
        self.chunk_index: Optional[faiss.Index] = None
        self.chunk_metadata: Dict[int, ChunkMeta] = {}
        self.chunk_texts: Dict[int, str] = {}
        self._chunk_next_id = 0
        
        # Mappings for hierarchy navigation
        self._section_to_doc: Dict[int, int] = {}  # section_faiss_id -> doc_faiss_id
        self._chunk_to_section: Dict[int, int] = {}  # chunk_faiss_id -> section_faiss_id
        
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize or load hierarchical indices"""
        try:
            self.index_path.mkdir(parents=True, exist_ok=True)
            
            # Try to load existing indices
            if self._load_indices():
                logger.info(
                    f"Loaded hierarchical indices: "
                    f"{len(self.document_metadata)} docs, "
                    f"{len(self.section_metadata)} sections, "
                    f"{len(self.chunk_metadata)} chunks"
                )
            else:
                # Create new indices
                self._create_new_indices()
                logger.info("Created new hierarchical indices")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize hierarchical index: {e}")
            return False
    
    def _create_new_indices(self):
        """Create new empty FAISS indices"""
        self.document_index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine sim
        self.section_index = faiss.IndexFlatIP(self.dimension)
        self.chunk_index = faiss.IndexFlatIP(self.dimension)
        
        self.document_metadata = {}
        self.section_metadata = {}
        self.chunk_metadata = {}
        self.section_texts = {}
        self.chunk_texts = {}
        
        self._doc_next_id = 0
        self._section_next_id = 0
        self._chunk_next_id = 0
    
    def _load_indices(self) -> bool:
        """Load indices from disk"""
        try:
            doc_index_path = self.index_path / "document.index"
            section_index_path = self.index_path / "section.index"
            chunk_index_path = self.index_path / "chunk.index"
            metadata_path = self.index_path / "metadata.pkl"
            
            if not all(p.exists() for p in [doc_index_path, section_index_path, 
                                            chunk_index_path, metadata_path]):
                return False
            
            # Load FAISS indices
            self.document_index = faiss.read_index(str(doc_index_path))
            self.section_index = faiss.read_index(str(section_index_path))
            self.chunk_index = faiss.read_index(str(chunk_index_path))
            
            # Load metadata
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)
            
            self.document_metadata = data.get("documents", {})
            self.section_metadata = data.get("sections", {})
            self.chunk_metadata = data.get("chunks", {})
            self.section_texts = data.get("section_texts", {})
            self.chunk_texts = data.get("chunk_texts", {})
            self._section_to_doc = data.get("section_to_doc", {})
            self._chunk_to_section = data.get("chunk_to_section", {})
            self._doc_next_id = data.get("doc_next_id", 0)
            self._section_next_id = data.get("section_next_id", 0)
            self._chunk_next_id = data.get("chunk_next_id", 0)
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load indices: {e}")
            return False
    
    def save(self) -> bool:
        """Save indices to disk"""
        try:
            self.index_path.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS indices
            faiss.write_index(self.document_index, str(self.index_path / "document.index"))
            faiss.write_index(self.section_index, str(self.index_path / "section.index"))
            faiss.write_index(self.chunk_index, str(self.index_path / "chunk.index"))
            
            # Save metadata
            data = {
                "documents": self.document_metadata,
                "sections": self.section_metadata,
                "chunks": self.chunk_metadata,
                "section_texts": self.section_texts,
                "chunk_texts": self.chunk_texts,
                "section_to_doc": self._section_to_doc,
                "chunk_to_section": self._chunk_to_section,
                "doc_next_id": self._doc_next_id,
                "section_next_id": self._section_next_id,
                "chunk_next_id": self._chunk_next_id
            }
            
            with open(self.index_path / "metadata.pkl", 'wb') as f:
                pickle.dump(data, f)
            
            logger.info("Saved hierarchical indices")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save indices: {e}")
            return False
    
    async def add_document(
        self,
        doc_meta: DocumentMeta,
        doc_embedding: np.ndarray,
        section_embeddings: Dict[str, Tuple[SectionMeta, np.ndarray, str]],
        chunk_embeddings: Dict[str, Tuple[ChunkMeta, np.ndarray, str]]
    ) -> int:
        """
        Add a document with its sections and chunks to the index.
        
        Args:
            doc_meta: Document metadata
            doc_embedding: Embedding for document summary
            section_embeddings: Dict of section_id -> (SectionMeta, embedding, summary_text)
            chunk_embeddings: Dict of chunk_id -> (ChunkMeta, embedding, chunk_text)
            
        Returns:
            FAISS ID for the document
        """
        if not self._initialized:
            raise RuntimeError("Index not initialized")
        
        # Normalize embeddings for cosine similarity
        doc_embedding = self._normalize(doc_embedding)
        
        # Add document
        doc_faiss_id = self._doc_next_id
        self.document_index.add(doc_embedding.reshape(1, -1).astype(np.float32))
        self.document_metadata[doc_faiss_id] = doc_meta
        self._doc_next_id += 1
        
        # Add sections
        section_faiss_ids = {}
        for section_id, (section_meta, section_emb, section_text) in section_embeddings.items():
            section_emb = self._normalize(section_emb)
            
            section_faiss_id = self._section_next_id
            self.section_index.add(section_emb.reshape(1, -1).astype(np.float32))
            self.section_metadata[section_faiss_id] = section_meta
            self.section_texts[section_faiss_id] = section_text
            self._section_to_doc[section_faiss_id] = doc_faiss_id
            section_faiss_ids[section_id] = section_faiss_id
            self._section_next_id += 1
        
        # Add chunks
        for chunk_id, (chunk_meta, chunk_emb, chunk_text) in chunk_embeddings.items():
            chunk_emb = self._normalize(chunk_emb)
            
            chunk_faiss_id = self._chunk_next_id
            self.chunk_index.add(chunk_emb.reshape(1, -1).astype(np.float32))
            self.chunk_metadata[chunk_faiss_id] = chunk_meta
            self.chunk_texts[chunk_faiss_id] = chunk_text
            
            # Link to section
            if chunk_meta.section_id in section_faiss_ids:
                self._chunk_to_section[chunk_faiss_id] = section_faiss_ids[chunk_meta.section_id]
            
            self._chunk_next_id += 1
        
        logger.info(
            f"Added document {doc_meta.document_id}: "
            f"{len(section_embeddings)} sections, {len(chunk_embeddings)} chunks"
        )
        
        return doc_faiss_id
    
    async def search_hierarchical(
        self,
        query_embedding: np.ndarray,
        top_k_sections: int = 3,
        top_k_chunks_per_section: int = 5,
        section_threshold: float = 0.5
    ) -> List[HierarchicalResult]:
        """
        Two-stage hierarchical search.
        
        Stage 1: Find relevant sections
        Stage 2: Find chunks within those sections
        
        Args:
            query_embedding: Query vector
            top_k_sections: Number of sections to retrieve in stage 1
            top_k_chunks_per_section: Chunks per section in stage 2
            section_threshold: Minimum section score
            
        Returns:
            List of HierarchicalResult with chunks and context
        """
        if not self._initialized:
            raise RuntimeError("Index not initialized")
        
        query_emb = self._normalize(query_embedding).reshape(1, -1).astype(np.float32)
        
        # Stage 1: Search sections
        if self.section_index.ntotal == 0:
            return []
        
        section_scores, section_ids = self.section_index.search(
            query_emb, 
            min(top_k_sections, self.section_index.ntotal)
        )
        
        # Filter by threshold and collect section info
        relevant_sections = []
        for score, section_faiss_id in zip(section_scores[0], section_ids[0]):
            if section_faiss_id < 0 or score < section_threshold:
                continue
            
            section_meta = self.section_metadata.get(int(section_faiss_id))
            if section_meta:
                relevant_sections.append((int(section_faiss_id), float(score), section_meta))
        
        if not relevant_sections:
            # Fall back to direct chunk search
            return await self._search_chunks_direct(query_emb, top_k_sections * top_k_chunks_per_section)
        
        # Stage 2: Search chunks within relevant sections
        results = []
        
        for section_faiss_id, section_score, section_meta in relevant_sections:
            # Find chunks belonging to this section
            section_chunk_ids = [
                chunk_id for chunk_id, sec_id in self._chunk_to_section.items()
                if sec_id == section_faiss_id
            ]
            
            if not section_chunk_ids:
                continue
            
            # Get embeddings for these chunks and search
            for chunk_faiss_id in section_chunk_ids[:top_k_chunks_per_section]:
                chunk_meta = self.chunk_metadata.get(chunk_faiss_id)
                chunk_text = self.chunk_texts.get(chunk_faiss_id, "")
                
                if not chunk_meta:
                    continue
                
                # Get document meta
                doc_faiss_id = self._section_to_doc.get(section_faiss_id)
                doc_meta = self.document_metadata.get(doc_faiss_id) if doc_faiss_id else None
                
                if not doc_meta:
                    continue
                
                # Calculate chunk score (would normally search, simplified here)
                # In full implementation, we'd search within section chunks
                chunk_score = section_score * 0.9  # Approximate
                
                results.append(HierarchicalResult(
                    chunk=chunk_meta,
                    chunk_text=chunk_text,
                    section=section_meta,
                    document=doc_meta,
                    chunk_score=chunk_score,
                    section_score=section_score
                ))
        
        # Sort by combined score
        results.sort(key=lambda r: r.combined_score, reverse=True)
        
        return results[:top_k_sections * top_k_chunks_per_section]
    
    async def _search_chunks_direct(
        self,
        query_embedding: np.ndarray,
        top_k: int
    ) -> List[HierarchicalResult]:
        """Direct chunk search without section filtering"""
        if self.chunk_index.ntotal == 0:
            return []
        
        scores, chunk_ids = self.chunk_index.search(
            query_embedding,
            min(top_k, self.chunk_index.ntotal)
        )
        
        results = []
        for score, chunk_faiss_id in zip(scores[0], chunk_ids[0]):
            if chunk_faiss_id < 0:
                continue
            
            chunk_meta = self.chunk_metadata.get(int(chunk_faiss_id))
            chunk_text = self.chunk_texts.get(int(chunk_faiss_id), "")
            
            if not chunk_meta:
                continue
            
            # Get section and document
            section_faiss_id = self._chunk_to_section.get(int(chunk_faiss_id))
            section_meta = self.section_metadata.get(section_faiss_id) if section_faiss_id else None
            
            doc_faiss_id = self._section_to_doc.get(section_faiss_id) if section_faiss_id else None
            doc_meta = self.document_metadata.get(doc_faiss_id) if doc_faiss_id else None
            
            if not doc_meta:
                continue
            
            results.append(HierarchicalResult(
                chunk=chunk_meta,
                chunk_text=chunk_text,
                section=section_meta,
                document=doc_meta,
                chunk_score=float(score)
            ))
        
        return results
    
    def _normalize(self, embedding: np.ndarray) -> np.ndarray:
        """L2 normalize embedding for cosine similarity"""
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "initialized": self._initialized,
            "total_documents": self.document_index.ntotal if self.document_index else 0,
            "total_sections": self.section_index.ntotal if self.section_index else 0,
            "total_chunks": self.chunk_index.ntotal if self.chunk_index else 0,
            "dimension": self.dimension
        }


# Global instance
hierarchical_index = HierarchicalIndex(dimension=rag_settings.FAISS_DIMENSION)
