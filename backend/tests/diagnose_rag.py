"""
RAG System Diagnostic Script
Run this to diagnose issues with vector store and embeddings
"""

import asyncio
import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import RAGDocument, RAGDocumentChunk
from app.services.rag.vector_store import vector_store_service
from app.services.rag.embedding_service import embedding_service
from app.services.rag.config import rag_settings

async def diagnose():
    print("="*60)
    print("RAG SYSTEM DIAGNOSTICS")
    print("="*60)
    
    # Check configuration
    print("\n1. Configuration Check:")
    print(f"   FAISS Index Path: {rag_settings.FAISS_INDEX_PATH}")
    print(f"   Index Type: {rag_settings.FAISS_INDEX_TYPE}")
    print(f"   Dimension: {rag_settings.FAISS_DIMENSION}")
    print(f"   Embedding Model: {rag_settings.OLLAMA_EMBEDDING_MODEL}")
    
    # Check if index files exist
    print("\n2. Index Files Check:")
    index_path = Path(rag_settings.FAISS_INDEX_PATH)
    index_file = index_path / "main_index.index"
    metadata_file = index_path / "main_index.metadata"
    
    print(f"   Index directory exists: {index_path.exists()}")
    print(f"   Index file exists: {index_file.exists()}")
    if index_file.exists():
        print(f"   Index file size: {index_file.stat().st_size} bytes")
    print(f"   Metadata file exists: {metadata_file.exists()}")
    if metadata_file.exists():
        print(f"   Metadata file size: {metadata_file.stat().st_size} bytes")
    
    # Check database
    print("\n3. Database Check:")
    db = SessionLocal()
    try:
        docs = db.query(RAGDocument).all()
        print(f"   Total documents: {len(docs)}")
        
        for doc in docs:
            print(f"\n   Document {doc.id}: {doc.filename}")
            print(f"     Status: {doc.status}")
            print(f"     Chunks: {doc.chunk_count}")
            print(f"     Tokens: {doc.total_tokens}")
            
            chunks = db.query(RAGDocumentChunk).filter(
                RAGDocumentChunk.document_id == doc.id
            ).all()
            print(f"     Actual chunks in DB: {len(chunks)}")
            
            if chunks:
                print(f"     First chunk preview: {chunks[0].chunk_text[:100]}...")
                print(f"     First chunk has vector_id: {chunks[0].vector_id}")
    finally:
        db.close()
    
    # Initialize services
    print("\n4. Service Initialization:")
    
    print("   Initializing embedding service...")
    embed_ok = await embedding_service.initialize()
    print(f"   Embedding service: {'✓' if embed_ok else '✗'}")
    
    print("   Initializing vector store...")
    vector_ok = vector_store_service.initialize()
    print(f"   Vector store: {'✓' if vector_ok else '✗'}")
    
    if vector_ok:
        stats = vector_store_service.get_stats()
        print(f"\n5. Vector Store Stats:")
        print(f"   Status: {stats['status']}")
        print(f"   Total vectors: {stats['total_vectors']}")
        print(f"   Metadata entries: {stats['metadata_entries']}")
        print(f"   Index type: {stats['index_type']}")
        print(f"   Dimension: {stats['dimension']}")
        print(f"   Index size: {stats['index_size_mb']} MB")
    
    # Test embedding generation
    print("\n6. Embedding Generation Test:")
    if embed_ok:
        try:
            test_text = "This is a test sentence for embedding generation."
            print(f"   Generating embedding for: '{test_text}'")
            embedding = await embedding_service.get_text_embedding(test_text)
            print(f"   Embedding shape: {embedding.shape}")
            print(f"   Embedding type: {embedding.dtype}")
            print(f"   First 5 values: {embedding[:5]}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n" + "="*60)
    print("DIAGNOSIS COMPLETE")
    print("="*60)
    
    # Recommendations
    print("\nRECOMMENDATIONS:")
    
    db = SessionLocal()
    docs = db.query(RAGDocument).all()
    db.close()
    
    if not vector_ok:
        print("✗ Vector store initialization failed - check logs for errors")
    elif vector_store_service.faiss_index.ntotal == 0 and docs:
        print("✗ Documents exist but no vectors in FAISS - run reindex:")
        print("  curl -X POST http://localhost:8000/api/rag/index/reindex \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"force\": true, \"clear_cache\": true}'")
    elif vector_store_service.faiss_index.ntotal > 0:
        print("✓ System appears healthy")
    else:
        print("• Upload a document to test the full pipeline")

if __name__ == "__main__":
    asyncio.run(diagnose())