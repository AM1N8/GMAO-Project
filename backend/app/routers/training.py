"""
Training router - Handles training priority analysis and skill management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import Skill, TechnicianSkill, EquipmentRequiredSkill, Technician
from app.schemas import (
    SkillCreate, SkillUpdate, SkillResponse,
    TechnicianSkillCreate, TechnicianSkillUpdate, TechnicianSkillResponse,
    EquipmentRequiredSkillCreate, EquipmentRequiredSkillUpdate, EquipmentRequiredSkillResponse,
    TrainingPriorityResponse
)
from app.services.training_service import TrainingService

router = APIRouter()


# ==================== TRAINING PRIORITY ENDPOINTS ====================

@router.get("/priorities", response_model=TrainingPriorityResponse)
def get_training_priorities(
    min_rpn: int = Query(100, ge=1, le=1000, description="Minimum RPN threshold"),
    risk_levels: Optional[str] = Query(
        None,
        description="Comma-separated risk levels (critical,high,medium,low)"
    ),
    skill_category: Optional[str] = Query(None, description="Filter by skill category"),
    mandatory_only: bool = Query(False, description="Only mandatory skills"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Get training priorities based on RPN values and skill gaps.
    
    **Algorithm:**
    1. Identify equipment with critical/high RPN values
    2. Determine required skills for that equipment
    3. Compare with available technician skills
    4. Calculate skill gap (technicians needed)
    5. Rank by priority score: RPN × skill_gap × skill_priority
    
    **Priority Score Calculation:**
    - Higher RPN → Higher priority
    - More skill gap → Higher priority
    - Mandatory skills → Higher priority
    
    **Use Cases:**
    - Plan training programs based on critical needs
    - Allocate training budget effectively
    - Identify skill shortages in high-risk areas
    - Ensure coverage for critical equipment
    """
    # Parse risk levels
    parsed_risk_levels = None
    if risk_levels:
        parsed_risk_levels = [level.strip() for level in risk_levels.split(',')]
    
    # Get priorities from service
    priorities = TrainingService.get_training_priorities(
        db=db,
        min_rpn=min_rpn,
        risk_levels=parsed_risk_levels,
        skill_category=skill_category,
        mandatory_only=mandatory_only,
        limit=limit
    )
    
    return priorities


@router.get("/technician/{technician_id}/needs")
def get_technician_training_needs(
    technician_id: int,
    min_rpn: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get training needs for a specific technician.
    
    Identifies skills that:
    - Are required for high-RPN equipment
    - The technician doesn't have or needs to improve
    - Would maximize their contribution to critical maintenance
    
    **Returns:**
    - Prioritized list of training needs
    - Current vs required proficiency levels
    - Context on why each skill is needed (RPN, equipment)
    """
    try:
        training_needs = TrainingService.get_technician_training_needs(
            db=db,
            technician_id=technician_id,
            min_rpn=min_rpn
        )
        
        return training_needs
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/skill-coverage")
def get_skill_coverage_report(
    skill_id: Optional[int] = Query(None, description="Filter by specific skill"),
    skill_category: Optional[str] = Query(None, description="Filter by skill category"),
    db: Session = Depends(get_db)
):
    """
    Generate skill coverage report for the organization.
    
    Shows:
    - How many technicians have each skill
    - Proficiency level distribution
    - Coverage percentage
    - Skills with critical gaps
    
    **Coverage Status:**
    - Adequate: ≥30% of technicians have the skill
    - Limited: 10-30% coverage
    - Critical: <10% coverage
    
    **Use Cases:**
    - Identify organization-wide skill gaps
    - Plan strategic training initiatives
    - Ensure redundancy for critical skills
    - Support workforce planning
    """
    coverage_report = TrainingService.get_skill_coverage_report(
        db=db,
        skill_id=skill_id,
        skill_category=skill_category
    )
    
    return coverage_report


# ==================== SKILL ENDPOINTS ====================

@router.post("/skills", response_model=SkillResponse, status_code=201)
def create_skill(
    skill: SkillCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new skill.
    
    **Validations:**
    - Skill name must be unique
    """
    # Check if skill name already exists
    existing = db.query(Skill).filter(
        Skill.skill_name == skill.skill_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Skill '{skill.skill_name}' already exists"
        )
    
    db_skill = Skill(**skill.model_dump())
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    
    return db_skill


@router.get("/skills", response_model=List[SkillResponse])
def list_skills(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    is_active: bool = True,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all skills with optional filtering.
    
    **Filters:**
    - category: Filter by skill category
    - is_active: Show only active skills
    - search: Search in skill name and description
    """
    query = db.query(Skill)
    
    if category:
        query = query.filter(Skill.category == category)
    
    query = query.filter(Skill.is_active == is_active)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Skill.skill_name.ilike(search_pattern)) |
            (Skill.description.ilike(search_pattern))
        )
    
    query = query.order_by(Skill.skill_name)
    
    skills = query.offset(skip).limit(limit).all()
    
    return skills


@router.get("/skills/{skill_id}", response_model=SkillResponse)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db)
):
    """Get skill by ID"""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return skill


@router.put("/skills/{skill_id}", response_model=SkillResponse)
def update_skill(
    skill_id: int,
    skill_update: SkillUpdate,
    db: Session = Depends(get_db)
):
    """Update skill by ID"""
    db_skill = db.query(Skill).filter(Skill.id == skill_id).first()
    
    if not db_skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check skill name uniqueness if being updated
    if skill_update.skill_name and skill_update.skill_name != db_skill.skill_name:
        existing = db.query(Skill).filter(
            Skill.skill_name == skill_update.skill_name
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Skill '{skill_update.skill_name}' already exists"
            )
    
    update_data = skill_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_skill, field, value)
    
    db.commit()
    db.refresh(db_skill)
    
    return db_skill


@router.delete("/skills/{skill_id}", status_code=204)
def delete_skill(
    skill_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Delete skill by ID.
    
    **Parameters:**
    - force: If True, deletes even if skill is assigned to technicians or equipment
    """
    db_skill = db.query(Skill).filter(Skill.id == skill_id).first()
    
    if not db_skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check if skill is in use
    technician_count = db.query(func.count(TechnicianSkill.id)).filter(
        TechnicianSkill.skill_id == skill_id
    ).scalar()
    
    equipment_count = db.query(func.count(EquipmentRequiredSkill.id)).filter(
        EquipmentRequiredSkill.skill_id == skill_id
    ).scalar()
    
    if (technician_count > 0 or equipment_count > 0) and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Skill is assigned to {technician_count} technicians and {equipment_count} equipment. Use force=true to delete anyway."
        )
    
    db.delete(db_skill)
    db.commit()
    
    return None


# ==================== TECHNICIAN SKILL ENDPOINTS ====================

@router.post("/technicians/{technician_id}/skills", response_model=TechnicianSkillResponse, status_code=201)
def assign_skill_to_technician(
    technician_id: int,
    skill_data: TechnicianSkillCreate,
    db: Session = Depends(get_db)
):
    """
    Assign a skill to a technician.
    
    **Validations:**
    - Technician must exist
    - Skill must exist
    - Same skill cannot be assigned twice
    """
    # Verify technician exists
    technician = db.query(Technician).filter(
        Technician.id == technician_id
    ).first()
    
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    # Verify skill exists
    skill = db.query(Skill).filter(Skill.id == skill_data.skill_id).first()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check if already assigned
    existing = db.query(TechnicianSkill).filter(
        TechnicianSkill.technician_id == technician_id,
        TechnicianSkill.skill_id == skill_data.skill_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Technician already has skill '{skill.skill_name}'"
        )
    
    # Create assignment
    technician_skill = TechnicianSkill(
        technician_id=technician_id,
        **skill_data.model_dump()
    )
    
    db.add(technician_skill)
    db.commit()
    db.refresh(technician_skill)
    
    return {
        **technician_skill.__dict__,
        "skill_name": skill.skill_name,
        "skill_category": skill.category
    }


@router.get("/technicians/{technician_id}/skills", response_model=List[TechnicianSkillResponse])
def get_technician_skills(
    technician_id: int,
    db: Session = Depends(get_db)
):
    """Get all skills for a technician"""
    technician = db.query(Technician).filter(
        Technician.id == technician_id
    ).first()
    
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    skills = db.query(TechnicianSkill, Skill).join(
        Skill,
        TechnicianSkill.skill_id == Skill.id
    ).filter(
        TechnicianSkill.technician_id == technician_id
    ).all()
    
    result = []
    for tech_skill, skill in skills:
        result.append({
            **tech_skill.__dict__,
            "skill_name": skill.skill_name,
            "skill_category": skill.category
        })
    
    return result


@router.put("/technicians/{technician_id}/skills/{skill_id}", response_model=TechnicianSkillResponse)
def update_technician_skill(
    technician_id: int,
    skill_id: int,
    skill_update: TechnicianSkillUpdate,
    db: Session = Depends(get_db)
):
    """Update technician skill proficiency and details"""
    technician_skill = db.query(TechnicianSkill).filter(
        TechnicianSkill.technician_id == technician_id,
        TechnicianSkill.skill_id == skill_id
    ).first()
    
    if not technician_skill:
        raise HTTPException(status_code=404, detail="Technician skill not found")
    
    update_data = skill_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(technician_skill, field, value)
    
    db.commit()
    db.refresh(technician_skill)
    
    skill = technician_skill.skill
    
    return {
        **technician_skill.__dict__,
        "skill_name": skill.skill_name,
        "skill_category": skill.category
    }


@router.delete("/technicians/{technician_id}/skills/{skill_id}", status_code=204)
def remove_skill_from_technician(
    technician_id: int,
    skill_id: int,
    db: Session = Depends(get_db)
):
    """Remove skill from technician"""
    technician_skill = db.query(TechnicianSkill).filter(
        TechnicianSkill.technician_id == technician_id,
        TechnicianSkill.skill_id == skill_id
    ).first()
    
    if not technician_skill:
        raise HTTPException(status_code=404, detail="Technician skill not found")
    
    db.delete(technician_skill)
    db.commit()
    
    return None


# ==================== EQUIPMENT REQUIRED SKILL ENDPOINTS ====================

@router.post("/equipment/{equipment_id}/required-skills", response_model=EquipmentRequiredSkillResponse, status_code=201)
def add_required_skill_to_equipment(
    equipment_id: int,
    skill_data: EquipmentRequiredSkillCreate,
    db: Session = Depends(get_db)
):
    """
    Add required skill to equipment.
    
    Defines which skills are needed to maintain the equipment.
    """
    from app.models import Equipment
    
    # Verify equipment exists
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id
    ).first()
    
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Verify skill exists
    skill = db.query(Skill).filter(Skill.id == skill_data.skill_id).first()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check if already assigned
    existing = db.query(EquipmentRequiredSkill).filter(
        EquipmentRequiredSkill.equipment_id == equipment_id,
        EquipmentRequiredSkill.skill_id == skill_data.skill_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Equipment already has required skill '{skill.skill_name}'"
        )
    
    # Create requirement
    equipment_skill = EquipmentRequiredSkill(
        equipment_id=equipment_id,
        **skill_data.model_dump()
    )
    
    db.add(equipment_skill)
    db.commit()
    db.refresh(equipment_skill)
    
    return {
        **equipment_skill.__dict__,
        "skill_name": skill.skill_name,
        "skill_category": skill.category
    }


@router.get("/equipment/{equipment_id}/required-skills", response_model=List[EquipmentRequiredSkillResponse])
def get_equipment_required_skills(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    """Get all required skills for equipment"""
    from app.models import Equipment
    
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id
    ).first()
    
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    skills = db.query(EquipmentRequiredSkill, Skill).join(
        Skill,
        EquipmentRequiredSkill.skill_id == Skill.id
    ).filter(
        EquipmentRequiredSkill.equipment_id == equipment_id
    ).all()
    
    result = []
    for eq_skill, skill in skills:
        result.append({
            **eq_skill.__dict__,
            "skill_name": skill.skill_name,
            "skill_category": skill.category
        })
    
    return result


@router.delete("/equipment/{equipment_id}/required-skills/{skill_id}", status_code=204)
def remove_required_skill_from_equipment(
    equipment_id: int,
    skill_id: int,
    db: Session = Depends(get_db)
):
    """Remove required skill from equipment"""
    equipment_skill = db.query(EquipmentRequiredSkill).filter(
        EquipmentRequiredSkill.equipment_id == equipment_id,
        EquipmentRequiredSkill.skill_id == skill_id
    ).first()
    
    if not equipment_skill:
        raise HTTPException(status_code=404, detail="Equipment required skill not found")
    
    db.delete(equipment_skill)
    db.commit()
    
    return None