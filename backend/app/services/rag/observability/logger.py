"""
RAG Logger
Structured logging for RAG requests with correlation IDs
"""

import logging
import json
import uuid
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger("rag.observability")


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class RAGLogEntry:
    """Structured log entry for RAG operations"""
    request_id: str
    timestamp: str
    event_type: str
    
    # Query info
    query_preview: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    
    # Routing
    handlers: Optional[List[str]] = None
    primary_handler: Optional[str] = None
    
    # Execution
    provider_used: Optional[str] = None
    latency_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    
    # Results
    success: bool = True
    cache_hit: bool = False
    results_count: Optional[int] = None
    
    # Errors
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class RAGLogger:
    """
    Structured logger for RAG system observability.
    
    Provides consistent logging format with correlation IDs
    for request tracing and debugging.
    """
    
    def __init__(self):
        self._current_request_id: Optional[str] = None
    
    def start_request(self, query: str) -> str:
        """Start a new request and return its correlation ID"""
        self._current_request_id = str(uuid.uuid4())[:8]
        
        self.log_event(
            event_type="request_started",
            query_preview=query[:50].replace("\n", " "),
            level=LogLevel.INFO
        )
        
        return self._current_request_id
    
    def log_event(
        self,
        event_type: str,
        level: LogLevel = LogLevel.INFO,
        **kwargs
    ):
        """Log a structured event"""
        entry = RAGLogEntry(
            request_id=self._current_request_id or "unknown",
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            **{k: v for k, v in kwargs.items() if v is not None}
        )
        
        log_func = getattr(logger, level.value)
        log_func(f"[RAG] {event_type}", extra=entry.to_dict())
    
    def log_routing(
        self,
        intent: str,
        confidence: float,
        handlers: List[str],
        primary_handler: str
    ):
        """Log routing decision"""
        self.log_event(
            event_type="query_routed",
            intent=intent,
            confidence=round(confidence, 3),
            handlers=handlers,
            primary_handler=primary_handler
        )
    
    def log_retrieval(
        self,
        handler: str,
        results_count: int,
        latency_ms: float,
        cache_hit: bool = False
    ):
        """Log retrieval results"""
        self.log_event(
            event_type="retrieval_completed",
            primary_handler=handler,
            results_count=results_count,
            latency_ms=round(latency_ms, 2),
            cache_hit=cache_hit
        )
    
    def log_llm_call(
        self,
        provider: str,
        latency_ms: float,
        tokens_used: int,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log LLM provider call"""
        self.log_event(
            event_type="llm_called",
            provider_used=provider,
            latency_ms=round(latency_ms, 2),
            tokens_used=tokens_used,
            success=success,
            error_message=error,
            level=LogLevel.INFO if success else LogLevel.ERROR
        )
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        **context
    ):
        """Log an error"""
        self.log_event(
            event_type="error",
            error_type=error_type,
            error_message=error_message,
            success=False,
            level=LogLevel.ERROR,
            **context
        )
    
    def end_request(
        self,
        success: bool = True,
        total_latency_ms: Optional[float] = None
    ):
        """End the current request"""
        self.log_event(
            event_type="request_completed",
            success=success,
            latency_ms=round(total_latency_ms, 2) if total_latency_ms else None,
            level=LogLevel.INFO if success else LogLevel.ERROR
        )
        
        self._current_request_id = None


# Global instance
rag_logger = RAGLogger()
