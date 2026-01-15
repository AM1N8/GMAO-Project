"""
Redis Cache Service for RAG System
Handles caching of embeddings and query results
"""

import json
import hashlib
import logging
from typing import Optional, List, Any, Dict
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import numpy as np

from app.services.rag.config import rag_settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service for RAG system"""
    
    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Redis connection pool"""
        if self._initialized:
            return True
        
        try:
            self.pool = ConnectionPool(
                host=rag_settings.REDIS_HOST,
                port=rag_settings.REDIS_PORT,
                db=rag_settings.REDIS_DB,
                password=rag_settings.REDIS_PASSWORD,
                max_connections=rag_settings.REDIS_MAX_CONNECTIONS,
                decode_responses=False  # We'll handle encoding ourselves
            )
            self.redis_client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            logger.info("Redis cache service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self._initialized = False
            return False
    
    async def close(self):
        """Close Redis connections"""
        if self.redis_client:
            await self.redis_client.close()
        if self.pool:
            await self.pool.disconnect()
        self._initialized = False
        logger.info("Redis cache service closed")
    
    def _generate_hash(self, text: str) -> str:
        """Generate SHA-256 hash for text"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _embedding_key(self, text: str, model: str) -> str:
        """Generate cache key for embeddings"""
        text_hash = self._generate_hash(text)
        return f"emb:{model}:{text_hash}"
    
    def _query_key(self, query: str, params: Dict[str, Any]) -> str:
        """Generate cache key for query results"""
        query_hash = self._generate_hash(query)
        params_str = json.dumps(params, sort_keys=True)
        params_hash = self._generate_hash(params_str)
        return f"query:{query_hash}:{params_hash}"
    
    async def get_embedding(self, text: str, model: str) -> Optional[np.ndarray]:
        """Retrieve cached embedding"""
        if not self._initialized or not rag_settings.ENABLE_CACHE:
            return None
        
        try:
            key = self._embedding_key(text, model)
            cached = await self.redis_client.get(key)
            
            if cached:
                # Deserialize numpy array
                embedding = np.frombuffer(cached, dtype=np.float32)
                logger.debug(f"Cache hit for embedding: {key[:50]}...")
                return embedding
            
            return None
        except Exception as e:
            logger.warning(f"Error retrieving cached embedding: {e}")
            return None
    
    async def set_embedding(
        self, 
        text: str, 
        model: str, 
        embedding: np.ndarray,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache embedding vector"""
        if not self._initialized or not rag_settings.ENABLE_CACHE:
            return False
        
        try:
            key = self._embedding_key(text, model)
            # Serialize numpy array
            serialized = embedding.astype(np.float32).tobytes()
            
            ttl = ttl or rag_settings.REDIS_CACHE_TTL
            await self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cached embedding: {key[:50]}...")
            return True
        except Exception as e:
            logger.warning(f"Error caching embedding: {e}")
            return False
    
    async def get_query_result(
        self, 
        query: str, 
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached query result"""
        if not self._initialized or not rag_settings.ENABLE_CACHE:
            return None
        
        try:
            key = self._query_key(query, params)
            cached = await self.redis_client.get(key)
            
            if cached:
                result = json.loads(cached.decode())
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return result
            
            return None
        except Exception as e:
            logger.warning(f"Error retrieving cached query: {e}")
            return None
    
    async def set_query_result(
        self,
        query: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache query result"""
        if not self._initialized or not rag_settings.ENABLE_CACHE:
            return False
        
        try:
            key = self._query_key(query, params)
            serialized = json.dumps(result).encode()
            
            ttl = ttl or rag_settings.REDIS_CACHE_TTL
            await self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cached query result: {query[:50]}...")
            return True
        except Exception as e:
            logger.warning(f"Error caching query result: {e}")
            return False
    
    async def clear_embeddings(self, model: Optional[str] = None) -> int:
        """Clear cached embeddings"""
        if not self._initialized:
            return 0
        
        try:
            pattern = f"emb:{model}:*" if model else "emb:*"
            keys = []
            
            async for key in self.redis_client.scan_iter(match=pattern, count=100):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} embedding cache entries")
                return deleted
            
            return 0
        except Exception as e:
            logger.error(f"Error clearing embeddings: {e}")
            return 0
    
    async def clear_queries(self) -> int:
        """Clear cached query results"""
        if not self._initialized:
            return 0
        
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match="query:*", count=100):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} query cache entries")
                return deleted
            
            return 0
        except Exception as e:
            logger.error(f"Error clearing queries: {e}")
            return 0
    
    async def clear_all(self) -> int:
        """Clear all RAG-related cache"""
        if not self._initialized:
            return 0
        
        emb_count = await self.clear_embeddings()
        query_count = await self.clear_queries()
        total = emb_count + query_count
        
        logger.info(f"Cleared total {total} cache entries")
        return total
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._initialized:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_client.info()
            
            # Count keys by pattern
            emb_count = 0
            query_count = 0
            
            async for _ in self.redis_client.scan_iter(match="emb:*", count=100):
                emb_count += 1
            
            async for _ in self.redis_client.scan_iter(match="query:*", count=100):
                query_count += 1
            
            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory_mb": info.get("used_memory", 0) / 1024 / 1024,
                "total_keys": await self.redis_client.dbsize(),
                "embedding_cache_keys": emb_count,
                "query_cache_keys": query_count,
                "hit_rate": info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}


# Global cache service instance
cache_service = CacheService()