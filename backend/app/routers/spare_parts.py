"""
Spare Parts router - Handles inventory management and stock alerts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import date, timedelta

from app.database import get_db
from app.models import SparePart, InterventionPart, Intervention
from app.schemas import (
    SparePartCreate, SparePartUpdate, SparePartResponse
)

router = APIRouter()


@router.get("/", response_model=List[SparePartResponse])
def list_spare_parts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    List all spare parts with optional filtering.
    
    **Filters:**
    - search: Search in designation, reference
    - low_stock_only: Show only parts below alert threshold
    """
    query = db.query(SparePart)
    
    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (SparePart.designation.ilike(search_pattern)) |
            (SparePart.reference.ilike(search_pattern))
        )
    
    # Apply low stock filter
    if low_stock_only:
        query = query.filter(SparePart.stock_actuel <= SparePart.seuil_alerte)
    
    # Order by designation
    query = query.order_by(SparePart.designation)
    
    # Apply pagination
    parts = query.offset(skip).limit(limit).all()
    
    # Add low stock flag
    result = []
    for part in parts:
        part_dict = part.__dict__.copy()
        part_dict['is_low_stock'] = part.stock_actuel <= part.seuil_alerte
        result.append(part_dict)
    
    return result


@router.get("/low-stock", response_model=List[SparePartResponse])
def get_low_stock_parts(
    db: Session = Depends(get_db)
):
    """
    Get all spare parts with stock levels at or below alert threshold.
    Useful for generating reorder lists.
    """
    parts = db.query(SparePart).filter(
        SparePart.stock_actuel <= SparePart.seuil_alerte
    ).order_by(
        (SparePart.stock_actuel - SparePart.seuil_alerte).asc()
    ).all()
    
    result = []
    for part in parts:
        part_dict = part.__dict__.copy()
        part_dict['is_low_stock'] = True
        result.append(part_dict)
    
    return result


@router.get("/{part_id}", response_model=SparePartResponse)
def get_spare_part(
    part_id: int,
    db: Session = Depends(get_db)
):
    """Get spare part by ID"""
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    
    if not part:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    part_dict = part.__dict__.copy()
    part_dict['is_low_stock'] = part.stock_actuel <= part.seuil_alerte
    
    return part_dict


@router.post("/", response_model=SparePartResponse, status_code=201)
def create_spare_part(
    part: SparePartCreate,
    db: Session = Depends(get_db)
):
    """
    Create new spare part.
    
    **Validations:**
    - Reference must be unique
    """
    # Check if reference already exists
    existing = db.query(SparePart).filter(
        SparePart.reference == part.reference
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Spare part with reference '{part.reference}' already exists"
        )
    
    # Create spare part
    db_part = SparePart(**part.model_dump())
    db.add(db_part)
    db.commit()
    db.refresh(db_part)
    
    db_part_dict = db_part.__dict__.copy()
    db_part_dict['is_low_stock'] = db_part.stock_actuel <= db_part.seuil_alerte
    
    return db_part_dict


@router.put("/{part_id}", response_model=SparePartResponse)
def update_spare_part(
    part_id: int,
    part_update: SparePartUpdate,
    db: Session = Depends(get_db)
):
    """Update spare part by ID"""
    db_part = db.query(SparePart).filter(SparePart.id == part_id).first()
    
    if not db_part:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    # Check reference uniqueness if being updated
    if part_update.reference and part_update.reference != db_part.reference:
        existing = db.query(SparePart).filter(
            SparePart.reference == part_update.reference
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Spare part with reference '{part_update.reference}' already exists"
            )
    
    # Update fields
    update_data = part_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_part, field, value)
    
    db.commit()
    db.refresh(db_part)
    
    db_part_dict = db_part.__dict__.copy()
    db_part_dict['is_low_stock'] = db_part.stock_actuel <= db_part.seuil_alerte
    
    return db_part_dict


@router.delete("/{part_id}", status_code=204)
def delete_spare_part(
    part_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Delete spare part by ID.
    
    **Parameters:**
    - force: If True, deletes even if part has been used in interventions
    """
    db_part = db.query(SparePart).filter(SparePart.id == part_id).first()
    
    if not db_part:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    # Check if part has been used
    usage_count = db.query(func.count(InterventionPart.id)).filter(
        InterventionPart.spare_part_id == part_id
    ).scalar()
    
    if usage_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Spare part has been used in {usage_count} interventions. Use force=true to delete anyway."
        )
    
    db.delete(db_part)
    db.commit()
    
    return None


@router.get("/{part_id}/consumption")
def get_spare_part_consumption(
    part_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Get consumption history for a spare part.
    Returns total quantity used and cost breakdown over time.
    """
    # Verify part exists
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    
    if not part:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    # Build query
    query = db.query(
        InterventionPart,
        Intervention.date_intervention,
        Intervention.equipment_id
    ).join(
        Intervention,
        InterventionPart.intervention_id == Intervention.id
    ).filter(
        InterventionPart.spare_part_id == part_id
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(Intervention.date_intervention >= start_date)
    
    if end_date:
        query = query.filter(Intervention.date_intervention <= end_date)
    
    # Order by date
    query = query.order_by(Intervention.date_intervention.desc())
    
    results = query.all()
    
    # Calculate statistics
    total_quantity = sum(r.InterventionPart.quantite for r in results)
    total_cost = sum(r.InterventionPart.cout_total for r in results)
    usage_count = len(results)
    
    # Build consumption history
    consumption_history = []
    for r in results:
        consumption_history.append({
            "date": r.date_intervention,
            "intervention_id": r.InterventionPart.intervention_id,
            "equipment_id": r.equipment_id,
            "quantity": r.InterventionPart.quantite,
            "unit_cost": r.InterventionPart.cout_unitaire,
            "total_cost": r.InterventionPart.cout_total
        })
    
    return {
        "spare_part_id": part_id,
        "spare_part_reference": part.reference,
        "spare_part_designation": part.designation,
        "current_stock": part.stock_actuel,
        "alert_threshold": part.seuil_alerte,
        "statistics": {
            "total_quantity_used": total_quantity,
            "total_cost": round(total_cost, 2),
            "usage_count": usage_count,
            "average_quantity_per_use": round(total_quantity / usage_count, 2) if usage_count > 0 else 0,
            "average_cost_per_use": round(total_cost / usage_count, 2) if usage_count > 0 else 0
        },
        "consumption_history": consumption_history,
        "period": {
            "start_date": start_date,
            "end_date": end_date
        }
    }


@router.patch("/{part_id}/stock")
def adjust_stock(
    part_id: int,
    quantity: int,
    operation: str = Query(..., pattern="^(add|subtract|set)$"),
    db: Session = Depends(get_db)
):
    """
    Adjust spare part stock level.
    
    **Operations:**
    - add: Add quantity to current stock
    - subtract: Subtract quantity from current stock
    - set: Set stock to exact quantity
    """
    db_part = db.query(SparePart).filter(SparePart.id == part_id).first()
    
    if not db_part:
        raise HTTPException(status_code=404, detail="Spare part not found")
    
    old_stock = db_part.stock_actuel
    
    if operation == "add":
        db_part.stock_actuel += quantity
    elif operation == "subtract":
        if db_part.stock_actuel < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot subtract {quantity}. Current stock is {db_part.stock_actuel}"
            )
        db_part.stock_actuel -= quantity
    elif operation == "set":
        if quantity < 0:
            raise HTTPException(status_code=400, detail="Stock cannot be negative")
        db_part.stock_actuel = quantity
    
    db.commit()
    db.refresh(db_part)
    
    return {
        "spare_part_id": part_id,
        "reference": db_part.reference,
        "designation": db_part.designation,
        "old_stock": old_stock,
        "new_stock": db_part.stock_actuel,
        "operation": operation,
        "quantity": quantity,
        "is_low_stock": db_part.stock_actuel <= db_part.seuil_alerte
    }