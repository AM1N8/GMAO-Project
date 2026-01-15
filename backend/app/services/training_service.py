"""
Training Service - Business logic for training priority analysis based on RPN and skill gaps.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, List, Dict
from datetime import datetime
import logging

from app.models import (
    Equipment, EquipmentRequiredSkill, Skill, Technician,
    TechnicianSkill, FailureMode, RPNAnalysis, TechnicianStatus
)
from app.services.amdec_service import AMDECService

logger = logging.getLogger(__name__)


class TrainingService:
    """Service class for training priority analysis"""
    
    @staticmethod
    def get_training_priorities(
        db: Session,
        min_rpn: int = 100,
        risk_levels: Optional[List[str]] = None,
        skill_category: Optional[str] = None,
        mandatory_only: bool = False,
        limit: Optional[int] = None
    ) -> Dict:
        """
        Calculate training priorities based on RPN values and skill gaps.
        
        Algorithm:
        1. Identify equipment with critical/high RPN values
        2. For each critical equipment, identify required skills
        3. Compare required skills with available technician skills
        4. Calculate skill gap (number of technicians needed)
        5. Calculate priority score: RPN × skill_gap_percentage × skill_priority
        6. Rank by priority score (descending)
        
        Args:
            db: Database session
            min_rpn: Minimum RPN threshold (default: 100)
            risk_levels: Filter by risk levels (critical, high, medium, low)
            skill_category: Filter by skill category
            mandatory_only: Only consider mandatory skills
            limit: Maximum number of results
        
        Returns:
            Dict with training priorities and statistics
        """
        # Step 1: Get critical equipment based on RPN
        critical_equipment = AMDECService.get_critical_equipment(db, min_rpn)
        
        # Apply risk level filter
        if risk_levels:
            critical_equipment = [
                eq for eq in critical_equipment
                if eq['risk_level'] in risk_levels
            ]
        
        if not critical_equipment:
            return {
                "total_priorities": 0,
                "critical_priorities": 0,
                "equipment_analyzed": 0,
                "skills_analyzed": 0,
                "priorities": [],
                "generated_at": datetime.now(),
                "filters_applied": {
                    "min_rpn": min_rpn,
                    "risk_levels": risk_levels,
                    "skill_category": skill_category,
                    "mandatory_only": mandatory_only
                }
            }
        
        equipment_ids = [eq['equipment_id'] for eq in critical_equipment]
        
        # Step 2: Get required skills for critical equipment
        query = db.query(
            EquipmentRequiredSkill,
            Equipment,
            Skill
        ).join(
            Equipment,
            EquipmentRequiredSkill.equipment_id == Equipment.id
        ).join(
            Skill,
            EquipmentRequiredSkill.skill_id == Skill.id
        ).filter(
            Equipment.id.in_(equipment_ids),
            Skill.is_active == True
        )
        
        # Apply filters
        if skill_category:
            query = query.filter(Skill.category == skill_category)
        
        if mandatory_only:
            query = query.filter(EquipmentRequiredSkill.is_mandatory == True)
        
        required_skills = query.all()
        
        # Get total number of active technicians
        total_technicians = db.query(func.count(Technician.id)).filter(
            Technician.status == TechnicianStatus.ACTIVE
        ).scalar()
        
        # Build priority list
        priorities = []
        skills_analyzed = set()
        
        for req_skill, equipment, skill in required_skills:
            skills_analyzed.add(skill.id)
            
            # Get RPN for this equipment
            equipment_rpn = next(
                (eq['max_rpn'] for eq in critical_equipment 
                 if eq['equipment_id'] == equipment.id),
                min_rpn
            )
            
            # Step 3: Count technicians with this skill at required level
            technicians_with_skill = db.query(func.count(TechnicianSkill.id)).join(
                Technician,
                TechnicianSkill.technician_id == Technician.id
            ).filter(
                TechnicianSkill.skill_id == skill.id,
                TechnicianSkill.proficiency_level >= req_skill.required_proficiency_level,
                TechnicianSkill.is_validated == True,
                Technician.status == TechnicianStatus.ACTIVE
            ).scalar()
            
            # Step 4: Calculate skill gap
            # Ideally, we want at least 2-3 technicians per critical skill
            # For mandatory skills, we need more coverage
            target_technicians = 3 if req_skill.is_mandatory else 2
            technicians_needed = max(0, target_technicians - technicians_with_skill)
            
            # Calculate skill gap percentage
            if total_technicians > 0:
                skill_gap_percentage = (technicians_needed / total_technicians) * 100
            else:
                skill_gap_percentage = 100.0
            
            # Step 5: Calculate priority score
            # Formula: RPN × skill_gap_percentage × skill_priority
            priority_score = (
                equipment_rpn * 
                skill_gap_percentage * 
                req_skill.priority
            )
            
            # Determine if this is a critical priority
            is_critical = (
                equipment_rpn >= 200 and 
                skill_gap_percentage >= 50 and
                req_skill.is_mandatory
            )
            
            priorities.append({
                "equipment_id": equipment.id,
                "equipment_designation": equipment.designation,
                "skill_id": skill.id,
                "skill_name": skill.skill_name,
                "skill_category": skill.category,
                "required_proficiency_level": req_skill.required_proficiency_level,
                "latest_rpn": equipment_rpn,
                "risk_level": AMDECService.get_risk_level(equipment_rpn),
                "num_technicians_with_skill": technicians_with_skill,
                "num_technicians_needed": technicians_needed,
                "skill_gap_percentage": round(skill_gap_percentage, 2),
                "priority_score": round(priority_score, 2),
                "priority_rank": 0,  # Will be set after sorting
                "is_mandatory_skill": req_skill.is_mandatory,
                "certification_required": skill.certification_required,
                "is_critical_priority": is_critical
            })
        
        # Step 6: Sort by priority score and assign ranks
        priorities.sort(key=lambda x: x['priority_score'], reverse=True)
        
        for idx, priority in enumerate(priorities, start=1):
            priority['priority_rank'] = idx
        
        # Apply limit
        if limit:
            priorities = priorities[:limit]
        
        # Calculate statistics
        critical_priorities = sum(
            1 for p in priorities if p['is_critical_priority']
        )
        
        return {
            "total_priorities": len(priorities),
            "critical_priorities": critical_priorities,
            "equipment_analyzed": len(equipment_ids),
            "skills_analyzed": len(skills_analyzed),
            "priorities": priorities,
            "generated_at": datetime.now(),
            "filters_applied": {
                "min_rpn": min_rpn,
                "risk_levels": risk_levels,
                "skill_category": skill_category,
                "mandatory_only": mandatory_only,
                "limit": limit
            }
        }
    
    @staticmethod
    def get_technician_training_needs(
        db: Session,
        technician_id: int,
        min_rpn: int = 100
    ) -> Dict:
        """
        Get training needs for a specific technician based on critical equipment.
        
        Args:
            db: Database session
            technician_id: ID of the technician
            min_rpn: Minimum RPN threshold
        
        Returns:
            Dict with technician's training needs
        """
        # Verify technician exists
        technician = db.query(Technician).filter(
            Technician.id == technician_id
        ).first()
        
        if not technician:
            raise ValueError(f"Technician with ID {technician_id} not found")
        
        # Get technician's current skills
        current_skills = db.query(
            TechnicianSkill.skill_id,
            TechnicianSkill.proficiency_level,
            Skill.skill_name,
            Skill.category
        ).join(
            Skill,
            TechnicianSkill.skill_id == Skill.id
        ).filter(
            TechnicianSkill.technician_id == technician_id,
            TechnicianSkill.is_validated == True
        ).all()
        
        current_skill_map = {
            skill.skill_id: {
                "level": skill.proficiency_level,
                "name": skill.skill_name,
                "category": skill.category
            }
            for skill in current_skills
        }
        
        # Get all training priorities
        all_priorities = TrainingService.get_training_priorities(
            db, min_rpn=min_rpn
        )
        
        # Filter for skills the technician doesn't have or needs to improve
        training_needs = []
        
        for priority in all_priorities['priorities']:
            skill_id = priority['skill_id']
            required_level = priority['required_proficiency_level']
            
            current_level = 0
            if skill_id in current_skill_map:
                current_level = current_skill_map[skill_id]['level']
            
            # Add to training needs if technician doesn't have skill or level is insufficient
            if current_level < required_level:
                training_needs.append({
                    **priority,
                    "current_proficiency_level": current_level,
                    "proficiency_gap": required_level - current_level,
                    "has_skill": current_level > 0
                })
        
        # Sort by priority score
        training_needs.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Assign ranks
        for idx, need in enumerate(training_needs, start=1):
            need['training_rank'] = idx
        
        return {
            "technician_id": technician_id,
            "technician_name": f"{technician.prenom} {technician.nom}",
            "technician_specialite": technician.specialite,
            "current_skills_count": len(current_skills),
            "training_needs_count": len(training_needs),
            "critical_needs_count": sum(
                1 for n in training_needs if n['is_critical_priority']
            ),
            "training_needs": training_needs,
            "generated_at": datetime.now()
        }
    
    @staticmethod
    def get_skill_coverage_report(
        db: Session,
        skill_id: Optional[int] = None,
        skill_category: Optional[str] = None
    ) -> Dict:
        """
        Generate a report on skill coverage across the organization.
        
        Args:
            db: Database session
            skill_id: Filter by specific skill
            skill_category: Filter by skill category
        
        Returns:
            Dict with skill coverage statistics
        """
        # Build query for skills
        query = db.query(Skill).filter(Skill.is_active == True)
        
        if skill_id:
            query = query.filter(Skill.id == skill_id)
        
        if skill_category:
            query = query.filter(Skill.category == skill_category)
        
        skills = query.all()
        
        total_technicians = db.query(func.count(Technician.id)).filter(
            Technician.status == TechnicianStatus.ACTIVE
        ).scalar()
        
        coverage_data = []
        
        for skill in skills:
            # Count technicians with this skill at each level
            level_distribution = {}
            for level in range(1, 6):
                count = db.query(func.count(TechnicianSkill.id)).join(
                    Technician,
                    TechnicianSkill.technician_id == Technician.id
                ).filter(
                    TechnicianSkill.skill_id == skill.id,
                    TechnicianSkill.proficiency_level == level,
                    TechnicianSkill.is_validated == True,
                    Technician.status == TechnicianStatus.ACTIVE
                ).scalar()
                level_distribution[f"level_{level}"] = count
            
            total_with_skill = sum(level_distribution.values())
            coverage_percentage = (
                (total_with_skill / total_technicians * 100)
                if total_technicians > 0 else 0
            )
            
            # Count equipment requiring this skill
            equipment_requiring = db.query(
                func.count(EquipmentRequiredSkill.id)
            ).filter(
                EquipmentRequiredSkill.skill_id == skill.id
            ).scalar()
            
            coverage_data.append({
                "skill_id": skill.id,
                "skill_name": skill.skill_name,
                "skill_category": skill.category,
                "difficulty_level": skill.difficulty_level,
                "certification_required": skill.certification_required,
                "total_technicians_with_skill": total_with_skill,
                "coverage_percentage": round(coverage_percentage, 2),
                "level_distribution": level_distribution,
                "equipment_requiring_skill": equipment_requiring,
                "coverage_status": (
                    "adequate" if coverage_percentage >= 30 else
                    "limited" if coverage_percentage >= 10 else
                    "critical"
                )
            })
        
        # Sort by coverage percentage (ascending) to highlight gaps
        coverage_data.sort(key=lambda x: x['coverage_percentage'])
        
        return {
            "total_skills_analyzed": len(coverage_data),
            "total_active_technicians": total_technicians,
            "skills_with_adequate_coverage": sum(
                1 for s in coverage_data if s['coverage_status'] == "adequate"
            ),
            "skills_with_critical_coverage": sum(
                1 for s in coverage_data if s['coverage_status'] == "critical"
            ),
            "skill_coverage": coverage_data,
            "generated_at": datetime.now()
        }