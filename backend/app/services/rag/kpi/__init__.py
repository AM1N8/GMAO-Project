"""
KPI Integration Package
Bridges RAG system with existing KPIService
"""

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name in ("KPIExecutor", "kpi_executor"):
        from app.services.rag.kpi import kpi_executor as ke_module
        return getattr(ke_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["KPIExecutor", "kpi_executor"]

