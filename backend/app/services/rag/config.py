"""
RAG System Configuration
Centralized configuration for all RAG components
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class RAGSettings(BaseSettings):
    """RAG System Settings"""
    
    # ==================== LLM Provider Configuration ====================
    
    # Groq Configuration (Primary Provider)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    GROQ_TIMEOUT: int = int(os.getenv("GROQ_TIMEOUT", "30"))
    
    # Ollama Configuration (Fallback Provider)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    
    # Provider Selection
    PRIMARY_LLM_PROVIDER: str = os.getenv("PRIMARY_LLM_PROVIDER", "groq")  # groq or ollama
    FALLBACK_LLM_PROVIDER: str = os.getenv("FALLBACK_LLM_PROVIDER", "ollama")
    ENABLE_FALLBACK: bool = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
    
    # ==================== Query Router Configuration ====================
    
    ENABLE_QUERY_ROUTER: bool = os.getenv("ENABLE_QUERY_ROUTER", "true").lower() == "true"
    INTENT_CONFIDENCE_THRESHOLD: float = float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.7"))
    ENABLE_GRAPH_SCOPE: bool = os.getenv("ENABLE_GRAPH_SCOPE", "true").lower() == "true"
    
    # ==================== Knowledge Graph Configuration ====================
    
    ENABLE_GRAPH_RAG: bool = os.getenv("ENABLE_GRAPH_RAG", "true").lower() == "true"
    GRAPH_STORE_PATH: str = os.getenv("GRAPH_STORE_PATH", "./data/knowledge_graph")
    GRAPH_MAX_HOPS: int = int(os.getenv("GRAPH_MAX_HOPS", "2"))
    
    # ==================== Hierarchical RAG Configuration ====================
    
    ENABLE_HIERARCHICAL_RAG: bool = os.getenv("ENABLE_HIERARCHICAL_RAG", "true").lower() == "true"
    HIERARCHY_TOP_K_SECTIONS: int = int(os.getenv("HIERARCHY_TOP_K_SECTIONS", "3"))
    HIERARCHY_TOP_K_CHUNKS: int = int(os.getenv("HIERARCHY_TOP_K_CHUNKS", "5"))
    
    # ==================== Redis Configuration ====================
    
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # 1 hour
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
    
    # ==================== FAISS Configuration ====================
    
    FAISS_INDEX_TYPE: str = os.getenv("FAISS_INDEX_TYPE", "Flat")  # Flat, IVF, HNSW
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "./data/faiss_indexes")
    FAISS_DIMENSION: int = int(os.getenv("FAISS_DIMENSION", "768"))  # nomic-embed-text dimension
    FAISS_NLIST: int = int(os.getenv("FAISS_NLIST", "100"))  # For IVF
    FAISS_NPROBE: int = int(os.getenv("FAISS_NPROBE", "10"))  # For IVF
    
    # ==================== Document Processing ====================
    
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    MAX_DOCUMENT_SIZE_MB: int = int(os.getenv("MAX_DOCUMENT_SIZE_MB", "50"))
    ALLOWED_FILE_TYPES: list = ["pdf", "txt", "docx", "md", "csv"]
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./data/uploads")
    
    # ==================== RAG Query Configuration ====================
    
    DEFAULT_TOP_K: int = int(os.getenv("DEFAULT_TOP_K", "5"))
    DEFAULT_SIMILARITY_THRESHOLD: float = float(os.getenv("DEFAULT_SIMILARITY_THRESHOLD", "0.7"))
    MAX_CONTEXT_LENGTH: int = int(os.getenv("MAX_CONTEXT_LENGTH", "4096"))
    
    # ==================== LLM Generation ====================
    
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.05"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    LLM_SYSTEM_PROMPT: str = os.getenv(
        "LLM_SYSTEM_PROMPT",
        "You are a helpful AI assistant for a maintenance management system (GMAO). "
        "Answer questions based on the provided context. Be concise and accurate. "
        "Always cite your sources when information comes from documents. "
        "If you don't know the answer, say so."
    )
    
    # ==================== Performance ====================
    
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "32"))
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    
    # ==================== Feature Flags ====================
    
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    ENABLE_QUERY_LOGGING: bool = os.getenv("ENABLE_QUERY_LOGGING", "true").lower() == "true"
    ENABLE_AUTO_REINDEX: bool = os.getenv("ENABLE_AUTO_REINDEX", "false").lower() == "true"
    ENABLE_SQL_PATH: bool = os.getenv("ENABLE_SQL_PATH", "true").lower() == "true"  # KPI queries
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


# Initialize settings
rag_settings = RAGSettings()

# Ensure directories exist
Path(rag_settings.FAISS_INDEX_PATH).mkdir(parents=True, exist_ok=True)
Path(rag_settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(rag_settings.GRAPH_STORE_PATH).mkdir(parents=True, exist_ok=True)
