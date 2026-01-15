"""
Embedding Service using Ollama
Generates embeddings for text using local models
"""

import logging
from typing import List, Optional
import numpy as np
import httpx

from llama_index.embeddings.ollama import OllamaEmbedding

from app.services.rag.config import rag_settings
from app.services.rag.cache_service import cache_service

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings using Ollama"""
    
    def __init__(self):
        self.model_name = rag_settings.OLLAMA_EMBEDDING_MODEL
        self.base_url = rag_settings.OLLAMA_BASE_URL
        self.embed_model: Optional[OllamaEmbedding] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Ollama embedding model"""
        try:
            # Check if Ollama is available
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                response.raise_for_status()
            
            # Initialize embedding model
            self.embed_model = OllamaEmbedding(
                model_name=self.model_name,
                base_url=self.base_url,
                ollama_additional_kwargs={"mirostat": 0}
            )
            
            # Test embedding
            test_embedding = await self.embed_model.aget_text_embedding("test")
            logger.info(
                f"Embedding service initialized with {self.model_name}, "
                f"dimension: {len(test_embedding)}"
            )
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            self._initialized = False
            return False
    
    async def get_text_embedding(
        self, 
        text: str,
        use_cache: bool = True
    ) -> np.ndarray:
        """Get embedding for a single text"""
        if not self._initialized:
            raise RuntimeError("Embedding service not initialized")
        
        # Try cache first
        if use_cache and rag_settings.ENABLE_CACHE:
            cached = await cache_service.get_embedding(text, self.model_name)
            if cached is not None:
                return cached
        
        try:
            # Generate embedding
            embedding = await self.embed_model.aget_text_embedding(text)
            embedding_array = np.array(embedding, dtype=np.float32)
            
            # Cache the result
            if use_cache and rag_settings.ENABLE_CACHE:
                await cache_service.set_embedding(text, self.model_name, embedding_array)
            
            return embedding_array
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def get_embeddings_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
        batch_size: Optional[int] = None
    ) -> List[np.ndarray]:
        """Get embeddings for multiple texts with batching"""
        if not self._initialized:
            raise RuntimeError("Embedding service not initialized")
        
        batch_size = batch_size or rag_settings.BATCH_SIZE
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = []
            
            for text in batch:
                embedding = await self.get_text_embedding(text, use_cache)
                batch_embeddings.append(embedding)
            
            embeddings.extend(batch_embeddings)
            
            if i + batch_size < len(texts):
                logger.debug(f"Processed {i + batch_size}/{len(texts)} embeddings")
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    async def get_query_embedding(self, query: str) -> np.ndarray:
        """Get embedding for a query (convenience method)"""
        return await self.get_text_embedding(query, use_cache=True)
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return rag_settings.FAISS_DIMENSION
    
    async def is_available(self) -> bool:
        """Check if Ollama service is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception:
            return False


# Global embedding service instance
embedding_service = EmbeddingService()