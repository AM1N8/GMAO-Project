"""
Hierarchical Document RAG Package
Two-stage retrieval preserving document structure
"""

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name in ("DocumentMeta", "SectionMeta", "ChunkMeta", "HierarchicalResult", "HierarchicalCitation"):
        from app.services.rag.hierarchy import document_hierarchy
        return getattr(document_hierarchy, name)
    elif name == "SectionExtractor":
        from app.services.rag.hierarchy.section_extractor import SectionExtractor
        return SectionExtractor
    elif name == "HierarchicalIndex":
        from app.services.rag.hierarchy.hierarchical_index import HierarchicalIndex
        return HierarchicalIndex
    elif name == "TwoStageRetriever":
        from app.services.rag.hierarchy.two_stage_retriever import TwoStageRetriever
        return TwoStageRetriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "DocumentMeta",
    "SectionMeta", 
    "ChunkMeta",
    "HierarchicalResult",
    "HierarchicalCitation",
    "SectionExtractor",
    "HierarchicalIndex",
    "TwoStageRetriever"
]

