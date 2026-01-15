"""
Technicians router - Manages maintenance personnel and workload tracking.
RBAC: Admin for create/update/delete, Supervisor+ for list/view
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models import Technician, TechnicianAssignment, Intervention, TechnicianStatus, UserRole
from app.schemas import (
    TechnicianCreate, TechnicianUpdate, TechnicianResponse,
    TechnicianWithStats, InterventionResponse
)
from app.security import (
    AuthUser, get_auth_user, require_role,
    require_admin, require_supervisor_or_admin
)

router = APIRouter()


@router.get("/", response_model=List[TechnicianResponse])
def list_technicians(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    specialite: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    List all technicians with optional filtering.
    
    **Filters:**
    - status: Filter by status (active, inactive, on_leave)
    - specialite: Filter by specialty
    - search: Search in name, email, specialty
    """
    query = db.query(Technician)
    
    # Apply filters
    if status:
        query = query.filter(Technician.status == status)
    
    if specialite:
        query = query.filter(Technician.specialite == specialite)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Technician.nom.ilike(search_pattern)) |
            (Technician.prenom.ilike(search_pattern)) |
            (Technician.email.ilike(search_pattern)) |
            (Technician.specialite.ilike(search_pattern))
        )
    
    # Order by name
    query = query.order_by(Technician.nom, Technician.prenom)
    
    # Apply pagination
    technicians = query.offset(skip).limit(limit).all()
    
    return technicians


@router.get("/{technician_id}", response_model=TechnicianWithStats)
def get_technician(
    technician_id: int,
    include_stats: bool = Query(True),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_supervisor_or_admin())
):
    """
    Get technician by ID with optional workload statistics.
    
    **Statistics included:**
    - Total interventions
    - Total hours worked
    - Total labor cost generated
    """
    technician = db.query(Technician).filter(
        Technician.id == technician_id
    ).first()
    
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    # Convert to dict for adding stats
    technician_dict = {
        "id": technician.id,
        "nom": technician.nom,
        "prenom": technician.prenom,
        "email": technician.email,
        "telephone": technician.telephone,
        "specialite": technician.specialite,
        "taux_horaire": technician.taux_horaire,
        "niveau_competence": technician.niveau_competence,
        "status": technician.status,
        "date_embauche": technician.date_embauche,
        "matricule": technician.matricule,
        "created_at": technician.created_at,
        "updated_at": technician.updated_at
    }
    
    if include_stats:
        # Build query for assignments
        query = db.query(TechnicianAssignment).filter(
            TechnicianAssignment.technician_id == technician_id
        )
        
        # Apply date filters if provided
        if start_date or end_date:
            query = query.join(
                Intervention,
                TechnicianAssignment.intervention_id == Intervention.id
            )
            
            if start_date:
                query = query.filter(Intervention.date_intervention >= start_date)
            
            if end_date:
                query = query.filter(Intervention.date_intervention <= end_date)
        
        # Calculate statistics
        stats = query.with_entities(
            func.count(TechnicianAssignment.id).label('total_interventions'),
            func.sum(TechnicianAssignment.nombre_heures).label('total_hours'),
            func.sum(TechnicianAssignment.cout_main_oeuvre).label('total_labor_cost')
        ).first()
        
        technician_dict.update({
            "total_interventions": stats.total_interventions or 0,
            "total_hours": float(stats.total_hours or 0),
            "total_labor_cost": float(stats.total_labor_cost or 0)
        })
    
    return technician_dict


@router.post("/", response_model=TechnicianResponse, status_code=201)
def create_technician(
    technician: TechnicianCreate,
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin())
):
    """
    Create new technician.
    
    **Validations:**
    - Email must be unique
    - Matricule must be unique (if provided)
    """
    # Check if email already exists
    existing_email = db.query(Technician).filter(
        Technician.email == technician.email
    ).first()
    
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail=f"Technician with email '{technician.email}' already exists"
        )
    
    # Check if matricule already exists
    if technician.matricule:
        existing_matricule = db.query(Technician).filter(
            Technician.matricule == technician.matricule
        ).first()
        
        if existing_matricule:
            raise HTTPException(
                status_code=400,
                detail=f"Technician with matricule '{technician.matricule}' already exists"
            )
    
    # Create technician
    db_technician = Technician(**technician.model_dump())
    db.add(db_technician)
    db.commit()
    db.refresh(db_technician)
    
    return db_technician


@router.put("/{technician_id}", response_model=TechnicianResponse)
def update_technician(
    technician_id: int,
    technician_update: TechnicianUpdate,
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin())
):
    """Update technician by ID"""
    db_technician = db.query(Technician).filter(
        Technician.id == technician_id
    ).first()
    
    if not db_technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    # Check email uniqueness if being updated
    if technician_update.email and technician_update.email != db_technician.email:
        existing = db.query(Technician).filter(
            Technician.email == technician_update.email
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Technician with email '{technician_update.email}' already exists"
            )
    
    # Update fields
    update_data = technician_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_technician, field, value)
    
    db.commit()
    db.refresh(db_technician)
    
    return db_technician


@router.delete("/{technician_id}", status_code=204)
def delete_technician(
    technician_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin())
):
    """
    Delete technician by ID.
    
    **Parameters:**
    - force: If True, deletes even if technician has assignment history
    
    **Note:** Past assignments will remain in history for audit purposes.
    """
    db_technician = db.query(Technician).filter(
        Technician.id == technician_id
    ).first()
    
    if not db_technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    # Check if technician has assignments
    assignment_count = db.query(func.count(TechnicianAssignment.id)).filter(
        TechnicianAssignment.technician_id == technician_id
    ).scalar()
    
    if assignment_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Technician has {assignment_count} assignment records. Use force=true to delete anyway."
        )
    
    db.delete(db_technician)
    db.commit()
    
    return None


@router.get("/{technician_id}/interventions", response_model=List[InterventionResponse])
def get_technician_interventions(
    technician_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Get all interventions assigned to a technician.
    """
    # Verify technician exists
    technician = db.query(Technician).filter(
        Technician.id == technician_id
    ).first()
    
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    # Build query
    query = db.query(Intervention).join(
        TechnicianAssignment,
        Intervention.id == TechnicianAssignment.intervention_id
    ).filter(
        TechnicianAssignment.technician_id == technician_id
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(Intervention.date_intervention >= start_date)
    
    if end_date:
        query = query.filter(Intervention.date_intervention <= end_date)
    
    # Order by date descending
    query = query.order_by(Intervention.date_intervention.desc())
    
    # Apply pagination
    interventions = query.offset(skip).limit(limit).all()
    
    return interventions


@router.get("/{technician_id}/workload")
def get_technician_workload(
    technician_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    group_by: str = Query("month", pattern="^(day|week|month|year)$"),
    db: Session = Depends(get_db)
):
    """
    Get detailed workload statistics for a technician.
    
    **Parameters:**
    - group_by: Granularity for time-based grouping (day, week, month, year)
    
    **Returns:**
    - Workload statistics grouped by time period
    - Total hours, interventions, and earnings
    - Average hours per intervention
    """
    # Verify technician exists
    technician = db.query(Technician).filter(
        Technician.id == technician_id
    ).first()
    
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    # Build query
    query = db.query(
        TechnicianAssignment,
        Intervention.date_intervention
    ).join(
        Intervention,
        TechnicianAssignment.intervention_id == Intervention.id
    ).filter(
        TechnicianAssignment.technician_id == technician_id
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(Intervention.date_intervention >= start_date)
    
    if end_date:
        query = query.filter(Intervention.date_intervention <= end_date)
    
    # Order by date
    query = query.order_by(Intervention.date_intervention)
    
    results = query.all()
    
    # Calculate overall statistics
    total_interventions = len(results)
    total_hours = sum(r.TechnicianAssignment.nombre_heures for r in results)
    total_earnings = sum(r.TechnicianAssignment.cout_main_oeuvre for r in results)
    
    # Group by time period
    from collections import defaultdict
    grouped = defaultdict(lambda: {"hours": 0, "interventions": 0, "earnings": 0})
    
    for r in results:
        date_key = r.date_intervention
        
        # Format date key based on grouping
        if group_by == "day":
            key = date_key.strftime("%Y-%m-%d")
        elif group_by == "week":
            key = f"{date_key.year}-W{date_key.isocalendar()[1]:02d}"
        elif group_by == "month":
            key = date_key.strftime("%Y-%m")
        else:  # year
            key = str(date_key.year)
        
        grouped[key]["hours"] += r.TechnicianAssignment.nombre_heures
        grouped[key]["interventions"] += 1
        grouped[key]["earnings"] += r.TechnicianAssignment.cout_main_oeuvre
    
    # Convert to list and sort
    workload_by_period = [
        {
            "period": period,
            "hours": round(data["hours"], 2),
            "interventions": data["interventions"],
            "earnings": round(data["earnings"], 2),
            "avg_hours_per_intervention": round(data["hours"] / data["interventions"], 2) if data["interventions"] > 0 else 0
        }
        for period, data in sorted(grouped.items())
    ]
    
    return {
        "technician_id": technician_id,
        "technician_name": f"{technician.prenom} {technician.nom}",
        "specialite": technician.specialite,
        "taux_horaire": technician.taux_horaire,
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "group_by": group_by
        },
        "summary": {
            "total_interventions": total_interventions,
            "total_hours": round(total_hours, 2),
            "total_earnings": round(total_earnings, 2),
            "average_hours_per_intervention": round(total_hours / total_interventions, 2) if total_interventions > 0 else 0
        },
        "workload_by_period": workload_by_period
    }