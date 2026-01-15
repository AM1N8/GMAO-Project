"""
Document Hierarchy Models
Data structures for hierarchical document representation
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of GMAO documents"""
    MANUAL = "manual"
    PROCEDURE = "procedure"
    REPORT = "report"
    SPECIFICATION = "specification"
    TRAINING = "training"
    AMDEC_FMEA = "amdec_fmea"
    UNKNOWN = "unknown"


@dataclass
class ChunkMeta:
    """Metadata for a text chunk (finest granularity)"""
    chunk_id: str
    document_id: int
    section_id: Optional[str]
    subsection_id: Optional[str]
    
    text: str
    chunk_index: int
    token_count: int
    
    page_number: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    
    # GMAO-specific metadata extracted from content
    equipment_mentions: List[str] = field(default_factory=list)
    part_numbers: List[str] = field(default_factory=list)
    
    # Vector info
    vector_id: Optional[str] = None
    embedding_cached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "section_id": self.section_id,
            "subsection_id": self.subsection_id,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "page_number": self.page_number,
            "equipment_mentions": self.equipment_mentions,
            "part_numbers": self.part_numbers,
            "vector_id": self.vector_id
        }


@dataclass
class SectionMeta:
    """Metadata for a document section"""
    section_id: str
    document_id: int
    
    title: str
    level: int  # 1 = top-level, 2 = subsection, etc.
    
    page_start: int
    page_end: Optional[int] = None
    
    # Summary embedding for section-level retrieval
    summary: Optional[str] = None
    vector_id: Optional[str] = None
    
    # Child sections and chunks
    subsections: List["SectionMeta"] = field(default_factory=list)
    chunk_ids: List[str] = field(default_factory=list)
    
    # Parent reference
    parent_section_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "document_id": self.document_id,
            "title": self.title,
            "level": self.level,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "chunk_count": len(self.chunk_ids),
            "subsection_count": len(self.subsections),
            "parent_section_id": self.parent_section_id,
            "vector_id": self.vector_id
        }
    
    def get_full_path(self) -> str:
        """Get section path like 'Chapter 2 > Maintenance > Lubrication'"""
        # This would be populated by the hierarchy builder
        return self.title


@dataclass
class DocumentMeta:
    """Metadata for a complete document"""
    document_id: int
    filename: str
    original_filename: str
    
    file_type: str
    file_size: int
    document_type: DocumentType
    
    # Document summary for top-level retrieval
    summary: Optional[str] = None
    vector_id: Optional[str] = None
    
    # Structure
    sections: List[SectionMeta] = field(default_factory=list)
    total_chunks: int = 0
    total_pages: Optional[int] = None
    
    # GMAO-specific
    equipment_covered: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # Timestamps
    indexed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "document_type": self.document_type.value,
            "total_pages": self.total_pages,
            "total_chunks": self.total_chunks,
            "section_count": len(self.sections),
            "equipment_covered": self.equipment_covered,
            "keywords": self.keywords,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "vector_id": self.vector_id
        }


@dataclass
class HierarchicalResult:
    """Result from hierarchical retrieval"""
    # The actual chunk
    chunk: ChunkMeta
    chunk_text: str
    
    # Parent context
    section: Optional[SectionMeta]
    document: DocumentMeta
    
    # Relevance scores
    chunk_score: float
    section_score: Optional[float] = None
    combined_score: float = 0.0
    
    def __post_init__(self):
        # Calculate combined score if not set
        if self.combined_score == 0.0:
            if self.section_score is not None:
                # Weight: 70% chunk, 30% section
                self.combined_score = 0.7 * self.chunk_score + 0.3 * self.section_score
            else:
                self.combined_score = self.chunk_score


@dataclass
class HierarchicalCitation:
    """Structured citation for RAG responses"""
    document_name: str
    document_id: int
    document_type: DocumentType
    
    section_title: Optional[str] = None
    section_path: Optional[str] = None  # Full path like "Ch 2 > Maintenance"
    subsection_title: Optional[str] = None
    
    page_number: Optional[int] = None
    chunk_excerpt: str = ""
    relevance_score: float = 0.0
    
    def to_string(self) -> str:
        """Format citation for display"""
        parts = [self.document_name]
        
        if self.section_title:
            parts.append(f"§ {self.section_title}")
        
        if self.subsection_title:
            parts.append(f"§§ {self.subsection_title}")
        
        if self.page_number:
            parts.append(f"(p. {self.page_number})")
        
        return " → ".join(parts)
    
    def to_markdown(self) -> str:
        """Format citation as markdown"""
        citation = f"**{self.document_name}**"
        
        if self.section_title:
            citation += f" - {self.section_title}"
        
        if self.page_number:
            citation += f" (page {self.page_number})"
        
        return citation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_name": self.document_name,
            "document_id": self.document_id,
            "document_type": self.document_type.value,
            "section_title": self.section_title,
            "section_path": self.section_path,
            "subsection_title": self.subsection_title,
            "page_number": self.page_number,
            "excerpt": self.chunk_excerpt[:200] if self.chunk_excerpt else "",
            "relevance_score": round(self.relevance_score, 4),
            "formatted": self.to_string()
        }


def create_citation_from_result(result: HierarchicalResult) -> HierarchicalCitation:
    """Create a citation from a hierarchical result"""
    return HierarchicalCitation(
        document_name=result.document.filename,
        document_id=result.document.document_id,
        document_type=result.document.document_type,
        section_title=result.section.title if result.section else None,
        section_path=result.section.get_full_path() if result.section else None,
        page_number=result.chunk.page_number,
        chunk_excerpt=result.chunk_text[:200] if result.chunk_text else "",
        relevance_score=result.combined_score
    )
