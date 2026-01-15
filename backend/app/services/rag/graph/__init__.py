"""
GraphRAG Package
Knowledge graph for relationship and causal reasoning
"""

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name in ("NodeType", "EdgeType", "GraphNode", "GraphEdge"):
        from app.services.rag.graph import schema
        return getattr(schema, name)
    elif name == "GMAOKnowledgeGraph":
        from app.services.rag.graph.graph_store import GMAOKnowledgeGraph
        return GMAOKnowledgeGraph
    elif name == "GraphBuilder":
        from app.services.rag.graph.graph_builder import GraphBuilder
        return GraphBuilder
    elif name in ("GraphQueryService", "GraphContext"):
        from app.services.rag.graph import graph_query
        return getattr(graph_query, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "NodeType",
    "EdgeType",
    "GraphNode",
    "GraphEdge",
    "GMAOKnowledgeGraph",
    "GraphBuilder",
    "GraphQueryService",
    "GraphContext"
]

