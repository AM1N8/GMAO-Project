"""
Interventions router - Handles all maintenance intervention endpoints.
Provides CRUD operations, status management, and parts/technicians assignment.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models import (
    Intervention, Equipment, InterventionPart, TechnicianAssignment,
    SparePart, Technician, InterventionStatus
)
from app.schemas import (
    InterventionCreate, InterventionUpdate, InterventionResponse,
    InterventionWithDetails, InterventionPartCreate, InterventionPartResponse,
    TechnicianAssignmentCreate, TechnicianAssignmentResponse
)

router = APIRouter()


@router.get("/", response_model=List[InterventionWithDetails])
def list_interventions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    equipment_id: Optional[int] = None,
    type_panne: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all interventions with optional filtering and pagination.
    
    **Filters:**
    - equipment_id: Filter by equipment
    - type_panne: Filter by failure type
    - status: Filter by status (open, in_progress, completed, closed, cancelled)
    - start_date: Filter from this date
    - end_date: Filter until this date
    - search: Search in resume_intervention, cause
    """
    query = db.query(Intervention).options(
        joinedload(Intervention.equipment)
    )
    
    # Apply filters
    if equipment_id:
        query = query.filter(Intervention.equipment_id == equipment_id)
    
    if type_panne:
        query = query.filter(Intervention.type_panne == type_panne)
    
    if status:
        query = query.filter(Intervention.status == status)
    
    if start_date:
        query = query.filter(Intervention.date_intervention >= start_date)
    
    if end_date:
        query = query.filter(Intervention.date_intervention <= end_date)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Intervention.resume_intervention.ilike(search_pattern),
                Intervention.cause.ilike(search_pattern),
                Intervention.organe.ilike(search_pattern)
            )
        )
    
    # Order by date descending
    query = query.order_by(Intervention.date_intervention.desc())
    
    # Apply pagination
    interventions = query.offset(skip).limit(limit).all()
    
    # Build response with details
    result = []
    for intervention in interventions:
        parts_count = db.query(func.count(InterventionPart.id)).filter(
            InterventionPart.intervention_id == intervention.id
        ).scalar()
        
        techs_count = db.query(func.count(TechnicianAssignment.id)).filter(
            TechnicianAssignment.intervention_id == intervention.id
        ).scalar()
        
        result.append({
            **intervention.__dict__,
            "equipment_designation": intervention.equipment.designation,
            "parts_count": parts_count,
            "technicians_count": techs_count
        })
    
    return result


@router.get("/{intervention_id}", response_model=InterventionWithDetails)
def get_intervention(
    intervention_id: int,
    db: Session = Depends(get_db)
):
    """Get intervention by ID with full details"""
    intervention = db.query(Intervention).options(
        joinedload(Intervention.equipment)
    ).filter(Intervention.id == intervention_id).first()
    
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    # Get counts
    parts_count = db.query(func.count(InterventionPart.id)).filter(
        InterventionPart.intervention_id == intervention.id
    ).scalar()
    
    techs_count = db.query(func.count(TechnicianAssignment.id)).filter(
        TechnicianAssignment.intervention_id == intervention.id
    ).scalar()
    
    return {
        **intervention.__dict__,
        "equipment_designation": intervention.equipment.designation,
        "parts_count": parts_count,
        "technicians_count": techs_count
    }


@router.post("/", response_model=InterventionResponse, status_code=201)
def create_intervention(
    intervention: InterventionCreate,
    db: Session = Depends(get_db)
):
    """
    Create new intervention.
    
    **Validations:**
    - Equipment must exist
    - Date intervention cannot be in future
    - Date demande must be <= date intervention
    """
    # Verify equipment exists
    equipment = db.query(Equipment).filter(
        Equipment.id == intervention.equipment_id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=404,
            detail=f"Equipment with id {intervention.equipment_id} not found"
        )
    
    # Create intervention
    db_intervention = Intervention(**intervention.model_dump())
    db.add(db_intervention)
    db.commit()
    db.refresh(db_intervention)
    
    return db_intervention


@router.put("/{intervention_id}", response_model=InterventionResponse)
def update_intervention(
    intervention_id: int,
    intervention_update: InterventionUpdate,
    db: Session = Depends(get_db)
):
    """Update intervention by ID"""
    db_intervention = db.query(Intervention).filter(
        Intervention.id == intervention_id
    ).first()
    
    if not db_intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    # Update fields
    update_data = intervention_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_intervention, field, value)
    
    db.commit()
    db.refresh(db_intervention)
    
    return db_intervention


@router.delete("/{intervention_id}", status_code=204)
def delete_intervention(
    intervention_id: int,
    db: Session = Depends(get_db)
):
    """Delete intervention by ID (cascade deletes parts and technician assignments)"""
    db_intervention = db.query(Intervention).filter(
        Intervention.id == intervention_id
    ).first()
    
    if not db_intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    db.delete(db_intervention)
    db.commit()
    
    return None


@router.patch("/{intervention_id}/status", response_model=InterventionResponse)
def update_intervention_status(
    intervention_id: int,
    status: InterventionStatus,
    db: Session = Depends(get_db)
):
    """Update intervention status only"""
    db_intervention = db.query(Intervention).filter(
        Intervention.id == intervention_id
    ).first()
    
    if not db_intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    db_intervention.status = status
    db.commit()
    db.refresh(db_intervention)
    
    return db_intervention


# ==================== SPARE PARTS MANAGEMENT ====================

@router.get("/{intervention_id}/parts", response_model=List[InterventionPartResponse])
def get_intervention_parts(
    intervention_id: int,
    db: Session = Depends(get_db)
):
    """Get all spare parts used in an intervention"""
    # Verify intervention exists
    intervention = db.query(Intervention).filter(
        Intervention.id == intervention_id
    ).first()
    
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    # Get parts with details
    parts = db.query(InterventionPart).options(
        joinedload(InterventionPart.spare_part)
    ).filter(InterventionPart.intervention_id == intervention_id).all()
    
    result = []
    for part in parts:
        result.append({
            **part.__dict__,
            "spare_part_designation": part.spare_part.designation,
            "spare_part_reference": part.spare_part.reference
        })
    
    return result


@router.post("/{intervention_id}/parts", response_model=InterventionPartResponse, status_code=201)
def add_spare_part_to_intervention(
    intervention_id: int,
    part_data: InterventionPartCreate,
    db: Session = Depends(get_db)
):
    """
    Add spare part to intervention.
    Automatically calculates total cost based on spare part unit cost.
    """
    # Verify intervention exists
    intervention = db.query(Intervention).filter(
        Intervention.id == intervention_id
    ).first()
    
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    # Verify spare part exists
    spare_part = db.query(SparePart).filter(
        SparePart.id == part_data.spare_part_id
    ).first()
    
    if not spare_part:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    # Calculate costs
    cout_unitaire = spare_part.cout_unitaire
    cout_total = part_data.quantite * cout_unitaire
    
    # Create intervention part
    intervention_part = InterventionPart(
        intervention_id=intervention_id,
        spare_part_id=part_data.spare_part_id,
        quantite=part_data.quantite,
        cout_unitaire=cout_unitaire,
        cout_total=cout_total
    )
    
    db.add(intervention_part)
    
    # Update intervention material cost
    intervention.cout_materiel += cout_total
    intervention.cout_total = intervention.cout_materiel + intervention.cout_main_oeuvre
    
    # Update spare part stock
    if spare_part.stock_actuel >= part_data.quantite:
        spare_part.stock_actuel -= int(part_data.quantite)
    
    db.commit()
    db.refresh(intervention_part)
    
    return {
        **intervention_part.__dict__,
        "spare_part_designation": spare_part.designation,
        "spare_part_reference": spare_part.reference
    }


@router.delete("/{intervention_id}/parts/{part_id}", status_code=204)
def remove_spare_part_from_intervention(
    intervention_id: int,
    part_id: int,
    db: Session = Depends(get_db)
):
    """Remove spare part from intervention"""
    intervention_part = db.query(InterventionPart).filter(
        InterventionPart.id == part_id,
        InterventionPart.intervention_id == intervention_id
    ).first()
    
    if not intervention_part:
        raise HTTPException(status_code=404, detail="Intervention part not found")
    
    # Update intervention cost
    intervention = intervention_part.intervention
    intervention.cout_materiel -= intervention_part.cout_total
    intervention.cout_total = intervention.cout_materiel + intervention.cout_main_oeuvre
    
    # Restore stock
    spare_part = intervention_part.spare_part
    spare_part.stock_actuel += int(intervention_part.quantite)
    
    db.delete(intervention_part)
    db.commit()
    
    return None


# ==================== TECHNICIAN ASSIGNMENT ====================

@router.get("/{intervention_id}/technicians", response_model=List[TechnicianAssignmentResponse])
def get_intervention_technicians(
    intervention_id: int,
    db: Session = Depends(get_db)
):
    """Get all technicians assigned to an intervention"""
    # Verify intervention exists
    intervention = db.query(Intervention).filter(
        Intervention.id == intervention_id
    ).first()
    
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    # Get assignments with technician details
    assignments = db.query(TechnicianAssignment).options(
        joinedload(TechnicianAssignment.technician)
    ).filter(TechnicianAssignment.intervention_id == intervention_id).all()
    
    result = []
    for assignment in assignments:
        result.append({
            **assignment.__dict__,
            "technician_nom": assignment.technician.nom,
            "technician_prenom": assignment.technician.prenom
        })
    
    return result


@router.post("/{intervention_id}/technicians", response_model=TechnicianAssignmentResponse, status_code=201)
def assign_technician_to_intervention(
    intervention_id: int,
    assignment_data: TechnicianAssignmentCreate,
    db: Session = Depends(get_db)
):
    """
    Assign technician to intervention.
    Automatically calculates labor cost based on technician hourly rate.
    """
    # Verify intervention exists
    intervention = db.query(Intervention).filter(
        Intervention.id == intervention_id
    ).first()
    
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    # Verify technician exists
    technician = db.query(Technician).filter(
        Technician.id == assignment_data.technician_id
    ).first()
    
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    # Check if already assigned
    existing = db.query(TechnicianAssignment).filter(
        TechnicianAssignment.intervention_id == intervention_id,
        TechnicianAssignment.technician_id == assignment_data.technician_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Technician already assigned to this intervention"
        )
    
    # Calculate labor cost
    taux_horaire = technician.taux_horaire
    cout_main_oeuvre = assignment_data.nombre_heures * taux_horaire
    
    # Create assignment
    assignment = TechnicianAssignment(
        intervention_id=intervention_id,
        technician_id=assignment_data.technician_id,
        nombre_heures=assignment_data.nombre_heures,
        taux_horaire=taux_horaire,
        cout_main_oeuvre=cout_main_oeuvre,
        date_debut=assignment_data.date_debut,
        date_fin=assignment_data.date_fin
    )
    
    db.add(assignment)
    
    # Update intervention costs and hours
    intervention.nombre_heures_mo += assignment_data.nombre_heures
    intervention.cout_main_oeuvre += cout_main_oeuvre
    intervention.cout_total = intervention.cout_materiel + intervention.cout_main_oeuvre
    
    db.commit()
    db.refresh(assignment)
    
    return {
        **assignment.__dict__,
        "technician_nom": technician.nom,
        "technician_prenom": technician.prenom
    }


@router.delete("/{intervention_id}/technicians/{assignment_id}", status_code=204)
def remove_technician_from_intervention(
    intervention_id: int,
    assignment_id: int,
    db: Session = Depends(get_db)
):
    """Remove technician assignment from intervention"""
    assignment = db.query(TechnicianAssignment).filter(
        TechnicianAssignment.id == assignment_id,
        TechnicianAssignment.intervention_id == intervention_id
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Technician assignment not found")
    
    # Update intervention costs and hours
    intervention = assignment.intervention
    intervention.nombre_heures_mo -= assignment.nombre_heures
    intervention.cout_main_oeuvre -= assignment.cout_main_oeuvre
    intervention.cout_total = intervention.cout_materiel + intervention.cout_main_oeuvre
    
    db.delete(assignment)
    db.commit()
    
    return None