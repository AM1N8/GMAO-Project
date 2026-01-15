"""
Two-Stage Retriever
Orchestrates section → chunk hierarchical retrieval
"""

import logging
from typing import List, Optional, Dict, Any
import numpy as np

from app.services.rag.config import rag_settings
from app.services.rag.hierarchy.document_hierarchy import (
    HierarchicalResult,
    HierarchicalCitation,
    create_citation_from_result
)
from app.services.rag.hierarchy.hierarchical_index import hierarchical_index

logger = logging.getLogger(__name__)


class TwoStageRetriever:
    """
    Orchestrates two-stage hierarchical retrieval.
    
    Stage 1: Section-level retrieval (coarse)
    Stage 2: Chunk-level retrieval within sections (fine)
    """
    
    def __init__(
        self,
        top_k_sections: Optional[int] = None,
        top_k_chunks: Optional[int] = None,
        section_threshold: float = 0.5
    ):
        self.top_k_sections = top_k_sections or rag_settings.HIERARCHY_TOP_K_SECTIONS
        self.top_k_chunks = top_k_chunks or rag_settings.HIERARCHY_TOP_K_CHUNKS
        self.section_threshold = section_threshold
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the retriever and underlying indices"""
        if not hierarchical_index._initialized:
            if not hierarchical_index.initialize():
                logger.error("Failed to initialize hierarchical index")
                return False
        
        self._initialized = True
        return True
    
    async def retrieve(
        self,
        query_embedding: np.ndarray,
        top_k_sections: Optional[int] = None,
        top_k_chunks: Optional[int] = None,
        document_filter: Optional[List[int]] = None,
        section_filter: Optional[List[str]] = None
    ) -> List[HierarchicalResult]:
        """
        Perform two-stage hierarchical retrieval.
        
        Args:
            query_embedding: Query vector
            top_k_sections: Override default section count
            top_k_chunks: Override default chunk count
            document_filter: Only search in these document IDs
            section_filter: Only search in these section IDs
            
        Returns:
            List of HierarchicalResult sorted by relevance
        """
        if not self._initialized:
            await self.initialize()
        
        k_sections = top_k_sections or self.top_k_sections
        k_chunks = top_k_chunks or self.top_k_chunks
        
        # Perform hierarchical search
        results = await hierarchical_index.search_hierarchical(
            query_embedding=query_embedding,
            top_k_sections=k_sections,
            top_k_chunks_per_section=k_chunks,
            section_threshold=self.section_threshold
        )
        
        # Apply filters if provided
        if document_filter:
            results = [
                r for r in results
                if r.document.document_id in document_filter
            ]
        
        if section_filter:
            results = [
                r for r in results
                if r.section and r.section.section_id in section_filter
            ]
        
        logger.debug(
            f"Retrieved {len(results)} chunks from hierarchical search "
            f"(sections={k_sections}, chunks_per_section={k_chunks})"
        )
        
        return results
    
    async def retrieve_with_citations(
        self,
        query_embedding: np.ndarray,
        **kwargs
    ) -> tuple[List[HierarchicalResult], List[HierarchicalCitation]]:
        """
        Retrieve with formatted citations.
        
        Returns:
            Tuple of (results, citations)
        """
        results = await self.retrieve(query_embedding, **kwargs)
        
        citations = [
            create_citation_from_result(result)
            for result in results
        ]
        
        return results, citations
    
    def format_context(
        self,
        results: List[HierarchicalResult],
        max_tokens: int = 4096,
        include_metadata: bool = True
    ) -> str:
        """
        Format retrieval results as context for LLM.
        
        Args:
            results: Hierarchical retrieval results
            max_tokens: Maximum context tokens
            include_metadata: Include section/document info
            
        Returns:
            Formatted context string
        """
        if not results:
            return ""
        
        context_parts = []
        current_tokens = 0
        
        for result in results:
            # Build chunk context
            parts = []
            
            if include_metadata:
                # Add source info
                source = f"[Source: {result.document.filename}"
                if result.section:
                    source += f" - {result.section.title}"
                if result.chunk.page_number:
                    source += f" (p.{result.chunk.page_number})"
                source += "]"
                parts.append(source)
            
            # Add content
            parts.append(result.chunk_text)
            
            chunk_context = "\n".join(parts)
            chunk_tokens = len(chunk_context.split())
            
            if current_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_context)
            current_tokens += chunk_tokens
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics"""
        index_stats = hierarchical_index.get_stats()
        return {
            "initialized": self._initialized,
            "top_k_sections": self.top_k_sections,
            "top_k_chunks": self.top_k_chunks,
            "section_threshold": self.section_threshold,
            **index_stats
        }


# Global instance
two_stage_retriever = TwoStageRetriever()
