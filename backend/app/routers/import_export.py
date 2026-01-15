"""
Import/Export router - Handles CSV imports and data exports.
RBAC: Supervisor or Admin for all import/export operations
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
import io
import logging

from app.database import get_db
from app.services.import_service import ImportService
from app.services.export_service import ExportService
from app.models import ImportLog, UserRole
from app.schemas import ImportResponse, ImportLogResponse
from app.security import AuthUser, require_supervisor_or_admin

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== IMPORT ENDPOINTS ====================

@router.post("/import/amdec", response_model=ImportResponse)
async def import_amdec_csv(
    file: UploadFile = File(...),
    user_id: str = Query("system", description="User performing the import"),
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Import AMDEC (Failure Mode and Effects Analysis) CSV file.
    
    **Expected columns:**
    - Désignation (equipment name) *required*
    - Type de panne (failure type)
    - Durée arrêt (h) (downtime in hours)
    - Date intervention *required*
    - Date demande (request date/time)
    - Cause (root cause)
    - Organe (affected component)
    - Résumé intervention (intervention description)
    - Coût matériel (material cost)
    
    **Features:**
    - Auto-detects encoding (UTF-8, Windows-1252, etc.)
    - Parses French date format (DD/MM/YYYY)
    - Converts comma decimals (1,5 → 1.5)
    - Creates equipment if doesn't exist
    - Transaction rollback on errors
    - Detailed error logging
    
    **Returns:** Import statistics and error details
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Validate file size (10MB max)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds 10MB limit"
            )
        
        # Import using service
        result = await ImportService.import_amdec_csv(
            db, content, file.filename, user_id
        )
        
        return result
    
    except Exception as e:
        logger.error(f"AMDEC import error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {str(e)}"
        )


@router.post("/import/gmao", response_model=ImportResponse)
async def import_gmao_csv(
    file: UploadFile = File(...),
    user_id: str = Query("system"),
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Import GMAO (CMMS) CSV file with spare parts data.
    
    **Expected columns:**
    - Désignation *required*
    - Type de panne
    - Durée arrêt (h)
    - Date intervention *required*
    - Coût matériel
    - [Pièce].Désignation (part name)
    - [Pièce].Référence (part reference)
    - [Pièce].Quantité (quantity used)
    
    **Features:**
    - Links spare parts to interventions
    - Creates spare parts if don't exist
    - Updates intervention costs
    - Handles multiple parts per intervention
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files accepted")
    
    try:
        content = await file.read()
        
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        result = await ImportService.import_gmao_csv(
            db, content, file.filename, user_id
        )
        
        return result
    
    except Exception as e:
        logger.error(f"GMAO import error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/import/workload", response_model=ImportResponse)
async def import_workload_csv(
    file: UploadFile = File(...),
    user_id: str = Query("system"),
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Import Workload CSV with technician assignments.
    
    **Expected columns:**
    - Désignation *required*
    - Type de panne
    - Date intervention *required*
    - Nombre d'heures MO (total labor hours)
    - Coût total intervention (total cost)
    - [MO interne].Nom (technician last name)
    - [MO interne].Prénom (technician first name)
    - [MO interne].Nombre d'heures (technician hours)
    
    **Features:**
    - Creates technicians if don't exist
    - Assigns technicians to interventions
    - Calculates labor costs
    - Updates intervention totals
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files accepted")
    
    try:
        content = await file.read()
        
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        result = await ImportService.import_workload_csv(
            db, content, file.filename, user_id
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Workload import error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/import/history", response_model=List[ImportLogResponse])
def get_import_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    import_type: Optional[str] = Query(None, pattern="^(amdec|gmao|workload)$"),
    status: Optional[str] = Query(None, pattern="^(success|partial|failed)$"),
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Get import history with filtering.
    
    **Filters:**
    - import_type: Filter by import type
    - status: Filter by status (success, partial, failed)
    
    **Returns:** List of import logs ordered by date (newest first)
    """
    query = db.query(ImportLog)
    
    if import_type:
        query = query.filter(ImportLog.import_type == import_type)
    
    if status:
        query = query.filter(ImportLog.status == status)
    
    query = query.order_by(ImportLog.created_at.desc())
    
    logs = query.offset(skip).limit(limit).all()
    
    return logs


# ==================== EXPORT ENDPOINTS ====================

@router.get("/export/interventions")
async def export_interventions(
    format: str = Query("csv", pattern="^(csv|excel)$"),
    equipment_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    type_panne: Optional[str] = None,
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Export interventions to CSV or Excel.
    
    **Formats:**
    - csv: UTF-8 with BOM for Excel compatibility
    - excel: XLSX with formatted columns
    
    **Filters:** Same as interventions list endpoint
    """
    try:
        # Get export data using service
        file_content, filename, media_type = await ExportService.export_interventions(
            db, format, equipment_id, start_date, end_date, type_panne
        )
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/equipment")
async def export_equipment(
    format: str = Query("csv", pattern="^(csv|excel)$"),
    include_stats: bool = Query(True, description="Include intervention statistics"),
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Export equipment list with optional statistics.
    
    **Includes:**
    - Equipment details
    - Total interventions
    - Total downtime
    - Total costs
    - MTBF, MTTR, Availability (if include_stats=true)
    """
    try:
        file_content, filename, media_type = await ExportService.export_equipment(
            db, format, include_stats
        )
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/spare-parts")
async def export_spare_parts(
    format: str = Query("csv", pattern="^(csv|excel)$"),
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Export spare parts inventory.
    
    **Options:**
    - low_stock_only: Export only parts below alert threshold
    """
    try:
        file_content, filename, media_type = await ExportService.export_spare_parts(
            db, format, low_stock_only
        )
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/kpi-report")
async def export_kpi_report(
    format: str = Query("excel", pattern="^(excel|pdf)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    equipment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Generate comprehensive KPI report.
    
    **Formats:**
    - excel: Multi-sheet workbook with charts
    - pdf: Formatted report with visualizations
    
    **Includes:**
    - Summary statistics
    - MTBF, MTTR, Availability
    - Failure distribution
    - Cost analysis
    - Trends and charts
    """
    try:
        file_content, filename, media_type = await ExportService.export_kpi_report(
            db, format, start_date, end_date, equipment_id
        )
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"Report generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/export/amdec-report")
async def export_amdec_report(
    format: str = Query("excel", pattern="^(excel|pdf)$"),
    risk_level: Optional[str] = Query(None, pattern="^(critical|high|medium|low)$"),
    equipment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Generate AMDEC/RPN analysis report.
    
    **Formats:**
    - excel: Multi-sheet with summary and detailed RPN analysis
    - pdf: Management-ready report with risk visualization
    
    **Filters:**
    - risk_level: Filter by risk level (critical, high, medium, low)
    - equipment_id: Filter by specific equipment
    
    **Includes:**
    - Risk summary by level
    - Top prioritized risks
    - G/O/D scores and RPN values
    - Corrective actions status
    """
    try:
        file_content, filename, media_type = await ExportService.export_amdec_report(
            db, format, risk_level, equipment_id
        )
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"AMDEC report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")