"""
Document Processing Service for RAG
Handles document loading, parsing, and chunking
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import DocxReader
# Use PyMuPDF (fitz) for better layout analysis and cleaner text extraction
from llama_index.readers.file import PyMuPDFReader

from app.services.rag.config import rag_settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process documents for RAG indexing"""
    
    def __init__(self):
        # Improved PDF reader
        self.pdf_reader = PyMuPDFReader()
        self.docx_reader = DocxReader()
        self.text_splitter = SentenceSplitter(
            chunk_size=rag_settings.CHUNK_SIZE,
            chunk_overlap=rag_settings.CHUNK_OVERLAP
        )
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    async def load_document(
        self, 
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Load and parse document based on file type"""
        
        path = Path(file_path)
        file_extension = path.suffix.lower()
        
        try:
            if file_extension == ".pdf":
                documents = await self._load_pdf(file_path)
            elif file_extension == ".docx":
                documents = await self._load_docx(file_path)
            elif file_extension in [".txt", ".md", ".csv"]:
                documents = await self._load_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Add metadata to all documents
            if metadata:
                for doc in documents:
                    if doc.metadata is None:
                        doc.metadata = {}
                    doc.metadata.update(metadata)
            
            logger.info(f"Loaded {len(documents)} document(s) from {path.name}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading document {path.name}: {e}")
            raise
    
    async def _load_pdf(self, file_path: str) -> List[Document]:
        """Load PDF document"""
        try:
            documents = self.pdf_reader.load_data(file_path)
            # Add page numbers to metadata
            for i, doc in enumerate(documents):
                if doc.metadata is None:
                    doc.metadata = {}
                doc.metadata["page_number"] = i + 1
            return documents
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            raise
    
    async def _load_docx(self, file_path: str) -> List[Document]:
        """Load DOCX document"""
        try:
            documents = self.docx_reader.load_data(file_path)
            return documents
        except Exception as e:
            logger.error(f"Error loading DOCX: {e}")
            raise
    
    async def _load_text(self, file_path: str) -> List[Document]:
        """Load plain text document"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            document = Document(
                text=content,
                metadata={
                    "file_path": file_path,
                    "file_name": Path(file_path).name
                }
            )
            return [document]
        except Exception as e:
            logger.error(f"Error loading text file: {e}")
            raise
    
    async def chunk_documents(
        self, 
        documents: List[Document]
    ) -> List[Dict[str, Any]]:
        """Split documents into chunks with proper metadata"""
        
        try:
            chunks = []
            
            for doc_idx, document in enumerate(documents):
                # Get base metadata from document
                base_metadata = document.metadata or {}
                
                # Split document into nodes
                nodes = self.text_splitter.get_nodes_from_documents([document])
                
                for chunk_idx, node in enumerate(nodes):
                    # Combine node metadata with base metadata
                    combined_metadata = {
                        **base_metadata,
                        "chunk_id": f"{doc_idx}_{chunk_idx}",
                        "chunk_index": chunk_idx,
                        "document_index": doc_idx,
                        "token_count": len(node.text.split())
                    }
                    
                    # Preserve page_number if present
                    if "page_number" in base_metadata:
                        combined_metadata["page_number"] = base_metadata["page_number"]
                    
                    chunk_data = {
                        "text": node.text,
                        "chunk_index": chunk_idx,
                        "document_index": doc_idx,
                        "metadata": combined_metadata
                    }
                    chunks.append(chunk_data)
            
            logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking documents: {e}")
            raise
    
    async def process_document(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Full document processing pipeline
        Returns processed chunks and metadata
        """
        
        start_time = datetime.now()
        
        try:
            # Calculate file hash
            file_hash = self.calculate_file_hash(file_path)
            
            # Prepare base metadata
            base_metadata = metadata or {}
            base_metadata["file_hash"] = file_hash
            
            # Load document
            documents = await self.load_document(file_path, base_metadata)
            
            # Create chunks with metadata preservation
            chunks = await self.chunk_documents(documents)
            
            # Validate chunks have required metadata
            for chunk in chunks:
                chunk_meta = chunk.get("metadata", {})
                if "document_id" not in chunk_meta and "document_id" in base_metadata:
                    chunk["metadata"]["document_id"] = base_metadata["document_id"]
                if "filename" not in chunk_meta and "filename" in base_metadata:
                    chunk["metadata"]["filename"] = base_metadata["filename"]
            
            # Calculate statistics
            total_tokens = sum(chunk["metadata"]["token_count"] for chunk in chunks)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "file_hash": file_hash,
                "chunks": chunks,
                "chunk_count": len(chunks),
                "total_tokens": total_tokens,
                "processing_time_seconds": processing_time,
                "status": "success"
            }
            
            logger.info(
                f"Processed document: {len(chunks)} chunks, "
                f"{total_tokens} tokens, {processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in document processing pipeline: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds()
            }
    
    def validate_file(self, file_path: str, max_size_mb: Optional[int] = None) -> Dict[str, Any]:
        """Validate file before processing"""
        
        path = Path(file_path)
        
        if not path.exists():
            return {"valid": False, "error": "File does not exist"}
        
        extension = path.suffix.lower()[1:]
        if extension not in rag_settings.ALLOWED_FILE_TYPES:
            return {
                "valid": False, 
                "error": f"File type '{extension}' not allowed. Allowed: {rag_settings.ALLOWED_FILE_TYPES}"
            }
        
        max_size = max_size_mb or rag_settings.MAX_DOCUMENT_SIZE_MB
        file_size_mb = path.stat().st_size / (1024 * 1024)
        
        if file_size_mb > max_size:
            return {
                "valid": False,
                "error": f"File size {file_size_mb:.2f}MB exceeds limit of {max_size}MB"
            }
        
        return {
            "valid": True,
            "file_size_mb": file_size_mb,
            "file_type": extension
        }


# Global document processor instance
document_processor = DocumentProcessor()