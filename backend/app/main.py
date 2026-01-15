from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import text
import logging

from app.database import init_db, engine
from app.routers import (
    equipment,
    interventions,
    spare_parts,
    technicians,
    kpi,
    import_export,
    rag,  
    chat,
    ocr,
    amdec,
    training,
    formation_priority,
    knowledge_base,
    guidance,
    prediction # Added prediction router
)
from app.services.rag.rag_service import rag_service

from app.security import get_current_user, get_current_user_optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with ML initialization"""
    # Startup
    logger.info("Starting ProAct GMAO API...")

    try:
        # Initialize database
        init_db()
        logger.info("Relational database initialized successfully")
        
        # Initialize RAG system
        logger.info("Initializing RAG system...")
        rag_initialized = await rag_service.initialize()
        
        if rag_initialized:
            logger.info("RAG system initialized successfully")
        else:
            logger.warning("RAG system initialization failed - RAG features will be unavailable")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down ProAct GMAO API...")
        
        # Shutdown RAG system
        await rag_service.shutdown()
        
        # Close database
        engine.dispose()
        
        logger.info("Shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="ProAct - GMAO with RAG",
    description=(
        "Maintenance Management System (GMAO) API with RAG Capabilities\n\n"
        "A comprehensive maintenance management system for tracking equipment, interventions, "
        "spare parts, and technicians with advanced KPI calculations.\n\n"
        "**New RAG Features:**\n"
        "- Document upload and indexing\n"
        "- Intelligent query system with AI-powered responses\n"
        "- Vector-based similarity search\n"
        "- Cached embeddings and query results\n"
        "- Document management and reindexing\n"
    ),
    version="2.0.0",
    contact={
        "name": "GMAO Support",
        "email": "mohamedaminedarraj@gmail.com"
    },
    license_info={
        "name": "MIT"
    },
    lifespan=lifespan
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# Exception handlers
# ----------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "error": str(exc)
        }
    )

# ----------------------------------------------------
# Routers
# ----------------------------------------------------
from app.security import get_auth_user, get_current_user

# ... existing code ...

app.include_router(
    equipment.router,
    prefix="/api/equipment",
    tags=["Equipment"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    interventions.router,
    prefix="/api/interventions",
    tags=["Interventions"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    spare_parts.router,
    prefix="/api/spare-parts",
    tags=["Spare Parts"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    technicians.router,
    prefix="/api/technicians",
    tags=["Technicians"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    kpi.router,
    prefix="/api/kpi",
    tags=["KPIs & Analytics"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    amdec.router,
    prefix="/api/amdec",
    tags=["AMDEC & RPN Analysis"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    training.router,
    prefix="/api/training",
    tags=["Training & Skills"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    formation_priority.router,
    prefix="/api/formation-priority",
    tags=["Formation Priority by Panne Type"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    knowledge_base.router,
    prefix="/api/knowledge-base",
    tags=["Knowledge Base"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    import_export.router,
    prefix="/api",
    tags=["Import/Export"],
    dependencies=[Depends(get_auth_user)]
)

# RAG Router
app.include_router(
    rag.router,
    prefix="/api/rag",
    tags=["RAG System"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    chat.router,
    prefix="/api/chat",
    tags=["LLM Chat"],
    dependencies=[Depends(get_auth_user)]
)

from app.routers import copilot
app.include_router(
    copilot.router,
    prefix="/api/copilot",
    tags=["Maintenance Copilot"],
    dependencies=[Depends(get_auth_user)]
)


app.include_router(
    ocr.router,
    prefix="/api/ocr",
    tags=["OCR (Vision AI)"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    guidance.router,
    prefix="/api/guidance",
    tags=["AI Guidance Agent"],
    dependencies=[Depends(get_auth_user)]
)

app.include_router(
    prediction.router,
    prefix="/api/predict",
    tags=["AI Forecast"],
    dependencies=[Depends(get_auth_user)]
)

# ----------------------------------------------------
# Root endpoints
# ----------------------------------------------------
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "message": "ProAct GMAO API with RAG is running",
        "version": "2.0.0",
        "features": [
            "Equipment Management",
            "Intervention Tracking",
            "Spare Parts Inventory",
            "Technician Management",
            "KPI Analytics",
            "RAG Document Intelligence",
            "AMDEC & RPN Analysis",  
            "Training Priority Analysis"  
        ],
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """
    Health check endpoint for monitoring
    """
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()

        # Check RAG system health
        rag_health = await rag_service.get_health(db)

        return {
            "status": "healthy",
            "database": "connected",
            "version": "2.0.0",
            "rag_system": {
                "status": rag_health["status"],
                "ollama": rag_health["ollama_available"],
                "redis": rag_health["redis_available"],
                "faiss": rag_health["faiss_available"]
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


@app.get("/api/stats", tags=["Root"])
async def get_api_stats():
    """
    Get API statistics - total counts of main entities
    """
    from app.database import get_db
    from app.models import (
        Equipment, Intervention, SparePart, Technician, RAGDocument,
        FailureMode, RPNAnalysis, Skill  # NOUVEAU
    )
    from sqlalchemy import func

    db = next(get_db())

    try:
        stats = {
            "equipment_count": db.query(func.count(Equipment.id)).scalar(),
            "intervention_count": db.query(func.count(Intervention.id)).scalar(),
            "spare_part_count": db.query(func.count(SparePart.id)).scalar(),
            "technician_count": db.query(func.count(Technician.id)).scalar(),
            "rag_document_count": db.query(func.count(RAGDocument.id)).scalar(),
            "failure_mode_count": db.query(func.count(FailureMode.id)).scalar(),  # NOUVEAU
            "rpn_analysis_count": db.query(func.count(RPNAnalysis.id)).scalar(),  # NOUVEAU
            "skill_count": db.query(func.count(Skill.id)).scalar(),  # NOUVEAU
            "equipment_status_breakdown": [
                {"status": s, "count": c} 
                for s, c in db.query(Equipment.status, func.count(Equipment.id)).group_by(Equipment.status).all()
            ]
        }
        return stats
    finally:
        db.close()


# Reload trigger update - AMDEC generation fixed
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )