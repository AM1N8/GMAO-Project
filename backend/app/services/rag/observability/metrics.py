"""
RAG Metrics
Track latency, usage, and performance metrics
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class ComponentMetrics:
    """Metrics for a single component"""
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count
    
    @property
    def success_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.success_count / self.request_count
    
    def record(self, latency_ms: float, success: bool):
        self.request_count += 1
        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_count": self.request_count,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2) if self.min_latency_ms != float('inf') else None,
            "max_latency_ms": round(self.max_latency_ms, 2),
            "error_count": self.error_count
        }


class RAGMetrics:
    """
    Collect and report RAG system metrics.
    
    Tracks:
    - Request counts by component
    - Latency statistics
    - Provider usage
    - Cache hit rates
    - Error rates
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # Overall metrics
        self.total_requests = 0
        self.total_successes = 0
        self.total_failures = 0
        
        # Component metrics
        self.components: Dict[str, ComponentMetrics] = defaultdict(ComponentMetrics)
        
        # Provider metrics
        self.provider_usage: Dict[str, int] = defaultdict(int)
        self.provider_fallback_count = 0
        
        # Intent metrics
        self.intent_counts: Dict[str, int] = defaultdict(int)
        
        # Cache metrics
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Start time
        self.started_at = datetime.now()
    
    def record_request(
        self,
        component: str,
        latency_ms: float,
        success: bool = True
    ):
        """Record a component request"""
        with self._lock:
            self.total_requests += 1
            if success:
                self.total_successes += 1
            else:
                self.total_failures += 1
            
            self.components[component].record(latency_ms, success)
    
    def record_provider_usage(
        self,
        provider: str,
        is_fallback: bool = False
    ):
        """Record LLM provider usage"""
        with self._lock:
            self.provider_usage[provider] += 1
            if is_fallback:
                self.provider_fallback_count += 1
    
    def record_intent(self, intent: str):
        """Record query intent"""
        with self._lock:
            self.intent_counts[intent] += 1
    
    def record_cache(self, hit: bool):
        """Record cache hit/miss"""
        with self._lock:
            if hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
    
    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    @property
    def overall_success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_successes / self.total_requests
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary"""
        uptime = datetime.now() - self.started_at
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "total_requests": self.total_requests,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "overall_success_rate": round(self.overall_success_rate, 4),
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "provider_usage": dict(self.provider_usage),
            "provider_fallback_count": self.provider_fallback_count,
            "intent_distribution": dict(self.intent_counts),
            "components": {
                name: metrics.to_dict()
                for name, metrics in self.components.items()
            }
        }
    
    def get_component_stats(self, component: str) -> Optional[Dict[str, Any]]:
        """Get stats for a specific component"""
        if component in self.components:
            return self.components[component].to_dict()
        return None
    
    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self.total_requests = 0
            self.total_successes = 0
            self.total_failures = 0
            self.components.clear()
            self.provider_usage.clear()
            self.provider_fallback_count = 0
            self.intent_counts.clear()
            self.cache_hits = 0
            self.cache_misses = 0
            self.started_at = datetime.now()


# Global instance
rag_metrics = RAGMetrics()
