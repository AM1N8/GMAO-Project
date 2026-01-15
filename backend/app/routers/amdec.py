"""
AMDEC router - Handles failure modes and RPN analysis endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import FailureMode, RPNAnalysis, Equipment
from app.schemas import (
    FailureModeCreate, FailureModeUpdate, FailureModeResponse,
    FailureModeWithLatestRPN, RPNAnalysisCreate, RPNAnalysisUpdate,
    RPNAnalysisResponse, RPNAnalysisWithDetails, RPNRankingResponse
)
from app.services.amdec_service import AMDECService
from app.security import get_current_user

router = APIRouter()


# ==================== FAILURE MODE ENDPOINTS ====================

@router.post("/failure-modes", response_model=FailureModeResponse, status_code=201)
def create_failure_mode(
    failure_mode: FailureModeCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new failure mode for equipment.
    
    **Validations:**
    - Equipment must exist
    - Mode name should be descriptive
    """
    # Verify equipment exists
    equipment = db.query(Equipment).filter(
        Equipment.id == failure_mode.equipment_id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=404,
            detail=f"Equipment with id {failure_mode.equipment_id} not found"
        )
    
    # Create failure mode
    db_failure_mode = FailureMode(**failure_mode.model_dump())
    db.add(db_failure_mode)
    db.commit()
    db.refresh(db_failure_mode)
    
    return db_failure_mode


@router.get("/failure-modes", response_model=List[FailureModeWithLatestRPN])
def list_failure_modes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    equipment_id: Optional[int] = None,
    is_active: bool = True,
    include_rpn: bool = True,
    db: Session = Depends(get_db)
):
    """
    List all failure modes with optional latest RPN data.
    
    **Filters:**
    - equipment_id: Filter by specific equipment
    - is_active: Show only active failure modes
    - include_rpn: Include latest RPN analysis data
    """
    query = db.query(FailureMode)
    
    if equipment_id:
        query = query.filter(FailureMode.equipment_id == equipment_id)
    
    query = query.filter(FailureMode.is_active == is_active)
    
    query = query.order_by(FailureMode.created_at.desc())
    
    failure_modes = query.offset(skip).limit(limit).all()
    
    # Add latest RPN data if requested
    result = []
    for fm in failure_modes:
        fm_dict = {
            "id": fm.id,
            "equipment_id": fm.equipment_id,
            "mode_name": fm.mode_name,
            "description": fm.description,
            "failure_cause": fm.failure_cause,
            "failure_effect": fm.failure_effect,
            "detection_method": fm.detection_method,
            "prevention_action": fm.prevention_action,
            "is_active": fm.is_active,
            "created_at": fm.created_at,
            "updated_at": fm.updated_at
        }
        
        if include_rpn:
            latest_rpn = AMDECService.get_latest_rpn_for_failure_mode(db, fm.id)
            if latest_rpn:
                fm_dict.update({
                    "latest_rpn": latest_rpn.rpn_value,
                    "latest_rpn_date": latest_rpn.analysis_date,
                    "gravity": latest_rpn.gravity,
                    "occurrence": latest_rpn.occurrence,
                    "detection": latest_rpn.detection
                })
            else:
                fm_dict.update({
                    "latest_rpn": None,
                    "latest_rpn_date": None,
                    "gravity": None,
                    "occurrence": None,
                    "detection": None
                })
        
        result.append(fm_dict)
    
    return result


@router.get("/failure-modes/{failure_mode_id}", response_model=FailureModeWithLatestRPN)
def get_failure_mode(
    failure_mode_id: int,
    db: Session = Depends(get_db)
):
    """Get failure mode by ID with latest RPN data"""
    failure_mode = db.query(FailureMode).filter(
        FailureMode.id == failure_mode_id
    ).first()
    
    if not failure_mode:
        raise HTTPException(status_code=404, detail="Failure mode not found")
    
    fm_dict = {
        "id": failure_mode.id,
        "equipment_id": failure_mode.equipment_id,
        "mode_name": failure_mode.mode_name,
        "description": failure_mode.description,
        "failure_cause": failure_mode.failure_cause,
        "failure_effect": failure_mode.failure_effect,
        "detection_method": failure_mode.detection_method,
        "prevention_action": failure_mode.prevention_action,
        "is_active": failure_mode.is_active,
        "created_at": failure_mode.created_at,
        "updated_at": failure_mode.updated_at
    }
    
    # Add latest RPN
    latest_rpn = AMDECService.get_latest_rpn_for_failure_mode(db, failure_mode_id)
    if latest_rpn:
        fm_dict.update({
            "latest_rpn": latest_rpn.rpn_value,
            "latest_rpn_date": latest_rpn.analysis_date,
            "gravity": latest_rpn.gravity,
            "occurrence": latest_rpn.occurrence,
            "detection": latest_rpn.detection
        })
    
    return fm_dict


@router.put("/failure-modes/{failure_mode_id}", response_model=FailureModeResponse)
def update_failure_mode(
    failure_mode_id: int,
    failure_mode_update: FailureModeUpdate,
    db: Session = Depends(get_db)
):
    """Update failure mode by ID"""
    db_failure_mode = db.query(FailureMode).filter(
        FailureMode.id == failure_mode_id
    ).first()
    
    if not db_failure_mode:
        raise HTTPException(status_code=404, detail="Failure mode not found")
    
    # Update fields
    update_data = failure_mode_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_failure_mode, field, value)
    
    db.commit()
    db.refresh(db_failure_mode)
    
    return db_failure_mode


@router.delete("/failure-modes/{failure_mode_id}", status_code=204)
def delete_failure_mode(
    failure_mode_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete failure mode by ID.
    
    **Note:** This will cascade delete all associated RPN analyses.
    """
    db_failure_mode = db.query(FailureMode).filter(
        FailureMode.id == failure_mode_id
    ).first()
    
    if not db_failure_mode:
        raise HTTPException(status_code=404, detail="Failure mode not found")
    
    db.delete(db_failure_mode)
    db.commit()
    
    return None


# ==================== RPN ANALYSIS ENDPOINTS ====================

@router.post("/rpn-analyses", response_model=RPNAnalysisResponse, status_code=201)
def create_rpn_analysis(
    rpn_data: RPNAnalysisCreate,
    db: Session = Depends(get_db)
):
    """
    Create RPN analysis for a failure mode.
    
    **RPN Calculation:**
    - RPN = G (Gravité) × O (Occurrence) × D (Détection)
    - Each component: 1-10 scale
    - Result: 1-1000
    
    **Risk Levels:**
    - Critical: RPN ≥ 200
    - High: 100 ≤ RPN < 200
    - Medium: 50 ≤ RPN < 100
    - Low: RPN < 50
    """
    try:
        rpn_analysis = AMDECService.create_rpn_analysis(
            db=db,
            failure_mode_id=rpn_data.failure_mode_id,
            gravity=rpn_data.gravity,
            occurrence=rpn_data.occurrence,
            detection=rpn_data.detection,
            analyst_name=rpn_data.analyst_name,
            comments=rpn_data.comments,
            corrective_action=rpn_data.corrective_action,
            action_due_date=rpn_data.action_due_date
        )
        
        return rpn_analysis
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rpn-analyses", response_model=List[RPNAnalysisWithDetails])
def list_rpn_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    failure_mode_id: Optional[int] = None,
    equipment_id: Optional[int] = None,
    min_rpn: Optional[int] = None,
    action_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List RPN analyses with filtering.
    
    **Filters:**
    - failure_mode_id: Filter by failure mode
    - equipment_id: Filter by equipment
    - min_rpn: Minimum RPN threshold
    - action_status: Filter by action status (pending, in_progress, completed)
    """
    query = db.query(RPNAnalysis).options(
        joinedload(RPNAnalysis.failure_mode).joinedload(FailureMode.equipment)
    )
    
    if failure_mode_id:
        query = query.filter(RPNAnalysis.failure_mode_id == failure_mode_id)
    
    if equipment_id:
        query = query.join(FailureMode).filter(
            FailureMode.equipment_id == equipment_id
        )
    
    if min_rpn:
        query = query.filter(RPNAnalysis.rpn_value >= min_rpn)
    
    if action_status:
        query = query.filter(RPNAnalysis.action_status == action_status)
    
    query = query.order_by(RPNAnalysis.analysis_date.desc())
    
    analyses = query.offset(skip).limit(limit).all()
    
    # Build response with details
    result = []
    for analysis in analyses:
        result.append({
            **analysis.__dict__,
            "failure_mode_name": analysis.failure_mode.mode_name,
            "equipment_id": analysis.failure_mode.equipment_id,
            "equipment_designation": analysis.failure_mode.equipment.designation
        })
    
    return result


@router.get("/rpn-analyses/{rpn_id}", response_model=RPNAnalysisWithDetails)
def get_rpn_analysis(
    rpn_id: int,
    db: Session = Depends(get_db)
):
    """Get RPN analysis by ID with details"""
    analysis = db.query(RPNAnalysis).options(
        joinedload(RPNAnalysis.failure_mode).joinedload(FailureMode.equipment)
    ).filter(RPNAnalysis.id == rpn_id).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="RPN analysis not found")
    
    return {
        **analysis.__dict__,
        "failure_mode_name": analysis.failure_mode.mode_name,
        "equipment_id": analysis.failure_mode.equipment_id,
        "equipment_designation": analysis.failure_mode.equipment.designation
    }


@router.put("/rpn-analyses/{rpn_id}", response_model=RPNAnalysisResponse)
def update_rpn_analysis(
    rpn_id: int,
    rpn_update: RPNAnalysisUpdate,
    db: Session = Depends(get_db)
):
    """
    Update RPN analysis.
    
    **Note:** RPN value is automatically recalculated if G, O, or D are updated.
    """
    try:
        update_data = rpn_update.model_dump(exclude_unset=True)
        
        rpn_analysis = AMDECService.update_rpn_analysis(
            db=db,
            rpn_analysis_id=rpn_id,
            **update_data
        )
        
        return rpn_analysis
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/rpn-analyses/{rpn_id}", status_code=204)
def delete_rpn_analysis(
    rpn_id: int,
    db: Session = Depends(get_db)
):
    """Delete RPN analysis by ID"""
    db_rpn = db.query(RPNAnalysis).filter(RPNAnalysis.id == rpn_id).first()
    
    if not db_rpn:
        raise HTTPException(status_code=404, detail="RPN analysis not found")
    
    db.delete(db_rpn)
    db.commit()
    
    return None


# ==================== RPN RANKING ENDPOINT ====================

@router.get("/rpn-ranking", response_model=RPNRankingResponse)
def get_rpn_ranking(
    equipment_id: Optional[int] = Query(None, description="Filter by specific equipment"),
    min_rpn: Optional[int] = Query(None, ge=1, le=1000, description="Minimum RPN threshold"),
    risk_levels: Optional[str] = Query(
        None, 
        description="Comma-separated risk levels (critical,high,medium,low)"
    ),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Get ranking of failure modes by RPN value (highest risk first).
    
    Shows only the latest RPN analysis for each failure mode.
    
    **Risk Level Classification:**
    - Critical: RPN ≥ 200
    - High: 100 ≤ RPN < 200
    - Medium: 50 ≤ RPN < 100
    - Low: RPN < 50
    
    **Use cases:**
    - Identify highest priority maintenance actions
    - Focus resources on critical risks
    - Track risk reduction over time
    """
    # Parse risk levels
    parsed_risk_levels = None
    if risk_levels:
        parsed_risk_levels = [level.strip() for level in risk_levels.split(',')]
    
    # Get ranking from service
    ranking_data = AMDECService.get_rpn_ranking(
        db=db,
        equipment_id=equipment_id,
        min_rpn=min_rpn,
        risk_levels=parsed_risk_levels,
        limit=limit
    )
    
    return ranking_data


@router.get("/critical-equipment")
def get_critical_equipment(
    min_rpn: int = Query(200, ge=1, le=1000, description="Minimum RPN threshold"),
    db: Session = Depends(get_db)
):
    """
    Get equipment with critical RPN values.
    
    Returns equipment with at least one failure mode above the RPN threshold,
    along with their maximum RPN value and count of critical failure modes.
    """
    critical_equipment = AMDECService.get_critical_equipment(db, min_rpn)
    
    return {
        "min_rpn_threshold": min_rpn,
        "critical_equipment_count": len(critical_equipment),
        "equipment": critical_equipment,
        "generated_at": datetime.now()
    }

@router.post("/auto-analyze")
async def trigger_auto_analysis(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger automated AMDEC analysis based on historical data.
    Generates Failure Modes and RPN values from intervention history.
    """
    try:
        result = AMDECService.generate_amdec_from_history(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
