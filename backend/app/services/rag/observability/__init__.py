"""
Observability Package
Structured logging and metrics for RAG system
"""

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name in ("RAGLogger", "rag_logger"):
        from app.services.rag.observability import logger as log_module
        return getattr(log_module, name)
    elif name in ("RAGMetrics", "rag_metrics"):
        from app.services.rag.observability import metrics as met_module
        return getattr(met_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["RAGLogger", "rag_logger", "RAGMetrics", "rag_metrics"]

