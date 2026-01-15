"""
Query Router Package
Intent classification and routing for RAG queries
"""

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name in ("IntentClassifier", "IntentType", "ClassificationResult"):
        from app.services.rag.router import intent_classifier
        return getattr(intent_classifier, name)
    elif name in ("QueryRouter", "RouteDecision"):
        from app.services.rag.router import query_router
        return getattr(query_router, name)
    elif name == "EntityExtractor":
        from app.services.rag.router.entity_extractor import EntityExtractor
        return EntityExtractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "IntentClassifier",
    "IntentType",
    "ClassificationResult",
    "QueryRouter",
    "RouteDecision",
    "EntityExtractor"
]

