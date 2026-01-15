"""
Equipment router - Handles all equipment/machine related endpoints.
Provides CRUD operations and equipment-specific statistics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models import Equipment, Intervention, EquipmentStatus
from app.schemas import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    EquipmentWithStats,
    InterventionResponse
)

router = APIRouter()


@router.get("/", response_model=List[EquipmentResponse])
def list_equipment(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all equipment with optional filtering and pagination.
    
    **Filters:**
    - status: Filter by equipment status
    - type: Filter by equipment type
    - search: Search in designation, type, location
    """
    query = db.query(Equipment)
    
    # Apply filters
    if status:
        query = query.filter(Equipment.status == status)
    
    if type:
        query = query.filter(Equipment.type == type)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Equipment.designation.ilike(search_pattern)) |
            (Equipment.type.ilike(search_pattern)) |
            (Equipment.location.ilike(search_pattern))
        )
    
    # Apply pagination
    equipment = query.offset(skip).limit(limit).all()
    
    return equipment


@router.get("/{equipment_id}", response_model=EquipmentWithStats)
def get_equipment(
    equipment_id: int,
    include_stats: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Get equipment by ID with optional statistics.
    
    **Statistics included:**
    - Total interventions count
    - Total downtime hours
    - Total cost
    - MTBF (Mean Time Between Failures)
    - MTTR (Mean Time To Repair)
    - Availability percentage
    """
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Convert to dict for adding stats
    equipment_dict = {
        "id": equipment.id,
        "designation": equipment.designation,
        "type": equipment.type,
        "location": equipment.location,
        "status": equipment.status,
        "acquisition_date": equipment.acquisition_date,
        "manufacturer": equipment.manufacturer,
        "model": equipment.model,
        "serial_number": equipment.serial_number,
        "created_at": equipment.created_at,
        "updated_at": equipment.updated_at
    }
    
    if include_stats:
        # Calculate statistics
        interventions = db.query(Intervention).filter(
            Intervention.equipment_id == equipment_id
        ).all()
        
        total_interventions = len(interventions)
        total_downtime = sum(i.duree_arret for i in interventions)
        total_cost = sum(i.cout_total for i in interventions)
        
        # Calculate MTTR (Mean Time To Repair)
        mttr = total_downtime / total_interventions if total_interventions > 0 else None
        
        # Calculate MTBF (simplified - requires operating hours)
        # Here we use time between interventions as approximation
        mtbf = None
        if total_interventions > 1:
            sorted_interventions = sorted(interventions, key=lambda x: x.date_intervention)
            time_diffs = []
            for i in range(1, len(sorted_interventions)):
                diff = (sorted_interventions[i].date_intervention - 
                       sorted_interventions[i-1].date_intervention).days * 24
                time_diffs.append(diff)
            mtbf = sum(time_diffs) / len(time_diffs) if time_diffs else None
        
        # Calculate availability (simplified - assumes 24/7 operation)
        availability = None
        if equipment.acquisition_date and total_interventions > 0:
            total_days = (date.today() - equipment.acquisition_date).days
            if total_days > 0:
                total_hours = total_days * 24
                availability = ((total_hours - total_downtime) / total_hours) * 100
        
        equipment_dict.update({
            "total_interventions": total_interventions,
            "total_downtime_hours": total_downtime,
            "total_cost": total_cost,
            "mtbf": mtbf,
            "mttr": mttr,
            "availability": availability
        })
    
    return equipment_dict


@router.post("/", response_model=EquipmentResponse, status_code=201)
def create_equipment(
    equipment: EquipmentCreate,
    db: Session = Depends(get_db)
):
    """
    Create new equipment.
    
    **Validations:**
    - Designation must be unique
    - Serial number must be unique (if provided)
    """
    # Check if designation already exists
    existing = db.query(Equipment).filter(
        Equipment.designation == equipment.designation
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Equipment with designation '{equipment.designation}' already exists"
        )
    
    # Check if serial number already exists
    if equipment.serial_number:
        existing_serial = db.query(Equipment).filter(
            Equipment.serial_number == equipment.serial_number
        ).first()
        
        if existing_serial:
            raise HTTPException(
                status_code=400,
                detail=f"Equipment with serial number '{equipment.serial_number}' already exists"
            )
    
    # Create new equipment
    db_equipment = Equipment(**equipment.model_dump())
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    
    return db_equipment


@router.put("/{equipment_id}", response_model=EquipmentResponse)
def update_equipment(
    equipment_id: int,
    equipment_update: EquipmentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update equipment by ID.
    
    Only provided fields will be updated.
    """
    db_equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not db_equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Check for designation uniqueness if being updated
    if equipment_update.designation and equipment_update.designation != db_equipment.designation:
        existing = db.query(Equipment).filter(
            Equipment.designation == equipment_update.designation
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Equipment with designation '{equipment_update.designation}' already exists"
            )
    
    # Update fields
    update_data = equipment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_equipment, field, value)
    
    db.commit()
    db.refresh(db_equipment)
    
    return db_equipment


@router.delete("/{equipment_id}", status_code=204)
def delete_equipment(
    equipment_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Delete equipment by ID.
    
    **Parameters:**
    - force: If True, deletes equipment even if it has associated interventions
    
    **Warning:** Deleting equipment will also delete all associated interventions (cascade delete).
    """
    db_equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not db_equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Check if equipment has interventions
    intervention_count = db.query(func.count(Intervention.id)).filter(
        Intervention.equipment_id == equipment_id
    ).scalar()
    
    if intervention_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Equipment has {intervention_count} associated interventions. Use force=true to delete anyway."
        )
    
    db.delete(db_equipment)
    db.commit()
    
    return None


@router.get("/{equipment_id}/interventions", response_model=List[InterventionResponse])
def get_equipment_interventions(
    equipment_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    type_panne: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all interventions for a specific equipment.
    
    **Filters:**
    - start_date: Filter interventions from this date
    - end_date: Filter interventions until this date
    - type_panne: Filter by failure type
    """
    # Check if equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Build query
    query = db.query(Intervention).filter(Intervention.equipment_id == equipment_id)
    
    # Apply filters
    if start_date:
        query = query.filter(Intervention.date_intervention >= start_date)
    
    if end_date:
        query = query.filter(Intervention.date_intervention <= end_date)
    
    if type_panne:
        query = query.filter(Intervention.type_panne == type_panne)
    
    # Order by date descending
    query = query.order_by(Intervention.date_intervention.desc())
    
    # Apply pagination
    interventions = query.offset(skip).limit(limit).all()
    
    return interventions


@router.get("/{equipment_id}/kpis")
def get_equipment_kpis(
    equipment_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive KPIs for a specific equipment.
    
    Returns MTBF, MTTR, availability, failure distribution, and cost analysis.
    """
    from app.services.kpi_service import KPIService
    
    # Check if equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Calculate KPIs using service
    kpis = {
        "equipment_id": equipment_id,
        "equipment_designation": equipment.designation,
        "mtbf": KPIService.calculate_mtbf(db, equipment_id, start_date, end_date),
        "mttr": KPIService.calculate_mttr(db, equipment_id, start_date, end_date),
        "availability": KPIService.calculate_availability(db, equipment_id, start_date, end_date),
        "failure_distribution": KPIService.get_failure_distribution(db, start_date, end_date, equipment_id),
        "cost_breakdown": KPIService.get_cost_breakdown(db, start_date, end_date, equipment_id)
    }
    
    return kpis