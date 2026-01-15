"""
Section Extractor
Extracts hierarchical structure from PDF and document files
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from app.services.rag.hierarchy.document_hierarchy import (
    DocumentMeta,
    SectionMeta,
    ChunkMeta,
    DocumentType
)

logger = logging.getLogger(__name__)

# Try to import PyMuPDF for better PDF parsing
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed. Install with: pip install PyMuPDF")


@dataclass
class DetectedHeader:
    """Detected header in a document"""
    text: str
    level: int
    page_number: int
    font_size: float
    is_bold: bool
    y_position: float


class SectionExtractor:
    """
    Extract hierarchical sections from documents.
    
    Supports PDF structure detection based on:
    - Font size (larger = higher level)
    - Bold text
    - Numbering patterns (1., 1.1, 1.1.1)
    - Common header keywords
    """
    
    # Common section header patterns
    SECTION_PATTERNS = [
        # Numbered: "1.", "1.1", "1.1.1", etc.
        (r"^(\d+\.)+\s*(\d+\.)?\s*(.+)$", "numbered"),
        # Roman: "I.", "II.", "III.", etc.
        (r"^(I{1,3}|IV|V|VI{1,3}|IX|X)\.\s*(.+)$", "roman"),
        # Letter: "A.", "B.", etc.
        (r"^[A-Z]\.\s*(.+)$", "letter"),
        # Chapter: "Chapter 1", "Chapitre 2"
        (r"^(Chapter|Chapitre|Section)\s+\d+[:\.]?\s*(.+)?$", "chapter"),
    ]
    
    # Keywords that often indicate sections
    SECTION_KEYWORDS = {
        1: ["introduction", "overview", "sommaire", "table of contents", 
            "conclusion", "references", "appendix", "annexe"],
        2: ["purpose", "scope", "safety", "sécurité", "maintenance",
            "procedure", "procédure", "troubleshooting", "dépannage",
            "specifications", "spécifications", "installation"]
    }
    
    # Minimum font size ratios for header detection
    MIN_H1_RATIO = 1.3  # 30% larger than body
    MIN_H2_RATIO = 1.15  # 15% larger than body
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._body_font_size: Optional[float] = None
    
    async def extract_structure(
        self,
        file_path: str,
        document_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentMeta:
        """
        Extract hierarchical structure from a document.
        
        Args:
            file_path: Path to the document file
            document_id: Database ID for the document
            metadata: Optional additional metadata
            
        Returns:
            DocumentMeta with sections and chunk info populated
        """
        path = Path(file_path)
        file_type = path.suffix.lower()[1:]
        
        # Initialize document meta
        doc_meta = DocumentMeta(
            document_id=document_id,
            filename=path.name,
            original_filename=path.name,
            file_type=file_type,
            file_size=path.stat().st_size,
            document_type=self._classify_document_type(path.name, metadata)
        )
        
        if file_type == "pdf" and PYMUPDF_AVAILABLE:
            return await self._extract_pdf_structure(file_path, doc_meta)
        else:
            # Text-based fallback
            return await self._extract_text_structure(file_path, doc_meta)
    
    async def _extract_pdf_structure(
        self,
        file_path: str,
        doc_meta: DocumentMeta
    ) -> DocumentMeta:
        """Extract structure from PDF using PyMuPDF"""
        try:
            doc = fitz.open(file_path)
            doc_meta.total_pages = len(doc)
            
            # First pass: detect body font size
            font_sizes = []
            for page in doc:
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                font_sizes.append(span["size"])
            
            if font_sizes:
                # Body font is typically the most common size
                from collections import Counter
                size_counts = Counter(font_sizes)
                self._body_font_size = size_counts.most_common(1)[0][0]
            else:
                self._body_font_size = 12.0
            
            # Second pass: detect headers
            headers = []
            for page_num, page in enumerate(doc):
                page_headers = self._detect_headers_in_page(page, page_num + 1)
                headers.extend(page_headers)
            
            # Build section hierarchy
            sections = self._build_section_hierarchy(headers, doc_meta.document_id)
            doc_meta.sections = sections
            
            # Extract text and create chunks per section
            all_chunks = []
            for section in sections:
                section_chunks = await self._extract_section_chunks(
                    doc, section, doc_meta.document_id
                )
                section.chunk_ids = [c.chunk_id for c in section_chunks]
                all_chunks.extend(section_chunks)
            
            doc_meta.total_chunks = len(all_chunks)
            
            # Generate document summary from first section or intro
            if all_chunks:
                first_chunks = all_chunks[:3]
                summary_text = " ".join([c.text for c in first_chunks])[:500]
                doc_meta.summary = summary_text
            
            # Extract equipment mentions from all chunks
            equipment = set()
            for chunk in all_chunks:
                equipment.update(chunk.equipment_mentions)
            doc_meta.equipment_covered = list(equipment)
            
            doc.close()
            
            logger.info(
                f"Extracted PDF structure: {len(sections)} sections, "
                f"{doc_meta.total_chunks} chunks from {doc_meta.filename}"
            )
            
            return doc_meta
            
        except Exception as e:
            logger.error(f"Error extracting PDF structure: {e}")
            # Fall back to text extraction
            return await self._extract_text_structure(file_path, doc_meta)
    
    def _detect_headers_in_page(
        self,
        page: "fitz.Page",
        page_number: int
    ) -> List[DetectedHeader]:
        """Detect headers in a PDF page"""
        headers = []
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" not in block:
                continue
            
            for line in block["lines"]:
                # Get line text and properties
                line_text = ""
                max_font_size = 0
                is_bold = False
                y_pos = line["bbox"][1]
                
                for span in line["spans"]:
                    line_text += span["text"]
                    max_font_size = max(max_font_size, span["size"])
                    if "bold" in span.get("font", "").lower():
                        is_bold = True
                
                line_text = line_text.strip()
                if not line_text or len(line_text) < 3:
                    continue
                
                # Check if this looks like a header
                header_level = self._detect_header_level(
                    line_text, max_font_size, is_bold
                )
                
                if header_level > 0:
                    headers.append(DetectedHeader(
                        text=line_text,
                        level=header_level,
                        page_number=page_number,
                        font_size=max_font_size,
                        is_bold=is_bold,
                        y_position=y_pos
                    ))
        
        return headers
    
    def _detect_header_level(
        self,
        text: str,
        font_size: float,
        is_bold: bool
    ) -> int:
        """
        Detect if text is a header and what level.
        
        Returns:
            0 if not a header, 1-3 for header level
        """
        text_lower = text.lower().strip()
        
        # Check font size ratio
        if self._body_font_size:
            ratio = font_size / self._body_font_size
        else:
            ratio = 1.0
        
        # Check for numbered patterns
        for pattern, pattern_type in self.SECTION_PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                # Count dots for numbering depth
                if pattern_type == "numbered":
                    dots = text.count('.')
                    return min(dots, 3)
                elif pattern_type == "chapter":
                    return 1
                else:
                    return 2
        
        # Check keywords
        for level, keywords in self.SECTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return level
        
        # Check by font size
        if ratio >= self.MIN_H1_RATIO and is_bold:
            return 1
        elif ratio >= self.MIN_H2_RATIO and is_bold:
            return 2
        elif ratio >= self.MIN_H2_RATIO:
            return 3
        
        return 0
    
    def _build_section_hierarchy(
        self,
        headers: List[DetectedHeader],
        document_id: int
    ) -> List[SectionMeta]:
        """Build hierarchical section structure from detected headers"""
        if not headers:
            # No headers detected, create single "Content" section
            return [SectionMeta(
                section_id=f"doc_{document_id}_sec_0",
                document_id=document_id,
                title="Content",
                level=1,
                page_start=1
            )]
        
        sections = []
        section_stack: List[SectionMeta] = []
        
        for i, header in enumerate(headers):
            section = SectionMeta(
                section_id=f"doc_{document_id}_sec_{i}",
                document_id=document_id,
                title=header.text,
                level=header.level,
                page_start=header.page_number
            )
            
            # Update page_end for previous section at same or higher level
            for prev in reversed(section_stack):
                if prev.level <= header.level and prev.page_end is None:
                    prev.page_end = header.page_number - 1
                    break
            
            # Find parent section
            while section_stack and section_stack[-1].level >= header.level:
                section_stack.pop()
            
            if section_stack:
                parent = section_stack[-1]
                section.parent_section_id = parent.section_id
                parent.subsections.append(section)
            else:
                # Top-level section
                sections.append(section)
            
            section_stack.append(section)
        
        return sections
    
    async def _extract_section_chunks(
        self,
        doc: "fitz.Document",
        section: SectionMeta,
        document_id: int
    ) -> List[ChunkMeta]:
        """Extract text chunks for a section"""
        chunks = []
        
        page_start = section.page_start - 1  # 0-indexed
        page_end = (section.page_end or doc.page_count) - 1
        
        # Extract text from section pages
        section_text = ""
        for page_num in range(page_start, min(page_end + 1, doc.page_count)):
            page = doc[page_num]
            section_text += page.get_text() + "\n"
        
        # Split into chunks
        text_chunks = self._split_into_chunks(section_text)
        
        for i, chunk_text in enumerate(text_chunks):
            chunk = ChunkMeta(
                chunk_id=f"{section.section_id}_chunk_{i}",
                document_id=document_id,
                section_id=section.section_id,
                subsection_id=None,
                text=chunk_text,
                chunk_index=i,
                token_count=len(chunk_text.split()),
                page_number=section.page_start + (i * self.chunk_size // 3000),  # Estimate
                equipment_mentions=self._extract_equipment_mentions(chunk_text),
                part_numbers=self._extract_part_numbers(chunk_text)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if not text.strip():
            return []
        
        words = text.split()
        chunks = []
        
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))
            start = end - self.chunk_overlap
        
        return chunks
    
    async def _extract_text_structure(
        self,
        file_path: str,
        doc_meta: DocumentMeta
    ) -> DocumentMeta:
        """Fallback text-based structure extraction"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create single section with all content
            section = SectionMeta(
                section_id=f"doc_{doc_meta.document_id}_sec_0",
                document_id=doc_meta.document_id,
                title="Content",
                level=1,
                page_start=1
            )
            
            # Create chunks
            text_chunks = self._split_into_chunks(content)
            chunks = []
            
            for i, chunk_text in enumerate(text_chunks):
                chunk = ChunkMeta(
                    chunk_id=f"{section.section_id}_chunk_{i}",
                    document_id=doc_meta.document_id,
                    section_id=section.section_id,
                    subsection_id=None,
                    text=chunk_text,
                    chunk_index=i,
                    token_count=len(chunk_text.split()),
                    equipment_mentions=self._extract_equipment_mentions(chunk_text),
                    part_numbers=self._extract_part_numbers(chunk_text)
                )
                chunks.append(chunk)
                section.chunk_ids.append(chunk.chunk_id)
            
            doc_meta.sections = [section]
            doc_meta.total_chunks = len(chunks)
            
            if chunks:
                doc_meta.summary = chunks[0].text[:500]
            
            return doc_meta
            
        except Exception as e:
            logger.error(f"Error extracting text structure: {e}")
            return doc_meta
    
    def _classify_document_type(
        self,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentType:
        """Classify document type from filename and metadata"""
        filename_lower = filename.lower()
        
        if any(kw in filename_lower for kw in ["manual", "manuel", "guide"]):
            return DocumentType.MANUAL
        elif any(kw in filename_lower for kw in ["procedure", "procédure", "sop"]):
            return DocumentType.PROCEDURE
        elif any(kw in filename_lower for kw in ["report", "rapport"]):
            return DocumentType.REPORT
        elif any(kw in filename_lower for kw in ["spec", "specification"]):
            return DocumentType.SPECIFICATION
        elif any(kw in filename_lower for kw in ["amdec", "fmea", "fmeca"]):
            return DocumentType.AMDEC_FMEA
        elif any(kw in filename_lower for kw in ["training", "formation"]):
            return DocumentType.TRAINING
        
        return DocumentType.UNKNOWN
    
    def _extract_equipment_mentions(self, text: str) -> List[str]:
        """Extract equipment references from text"""
        # Simple pattern matching - could be enhanced with NER
        patterns = [
            r"(?:equipment|équipement|machine|pump|pompe|motor|moteur|valve|compressor)\s*[:-]?\s*([A-Z0-9][A-Z0-9\-_]+)",
            r"([A-Z]{2,4}[-_]?\d{2,5})",  # Equipment codes like "PMP-001"
        ]
        
        mentions = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            mentions.update(matches)
        
        return list(mentions)[:10]  # Limit to 10
    
    def _extract_part_numbers(self, text: str) -> List[str]:
        """Extract part numbers from text"""
        patterns = [
            r"(?:part|pièce|ref|référence)[:\s#]*([A-Z0-9][-A-Z0-9]{3,20})",
            r"(?:P/N|PN)[:\s]*([A-Z0-9][-A-Z0-9]{3,20})",
        ]
        
        parts = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            parts.update(matches)
        
        return list(parts)[:10]


# Global instance
section_extractor = SectionExtractor()
