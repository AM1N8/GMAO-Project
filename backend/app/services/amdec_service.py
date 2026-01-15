"""
AMDEC Service - Business logic for RPN calculation and AMDEC analysis.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import Optional, List, Dict
from datetime import date, datetime
import logging

from app.models import FailureMode, RPNAnalysis, Equipment

logger = logging.getLogger(__name__)


class AMDECService:
    """Service class for AMDEC and RPN operations"""
    
    @staticmethod
    def calculate_rpn(gravity: int, occurrence: int, detection: int) -> int:
        """
        Calculate RPN (Risk Priority Number).
        
        Formula: RPN = G × O × D
        where:
        - G (Gravity/Severity): 1-10
        - O (Occurrence/Frequency): 1-10
        - D (Detection difficulty): 1-10
        
        Args:
            gravity: Severity score (1-10)
            occurrence: Occurrence score (1-10)
            detection: Detection difficulty score (1-10)
        
        Returns:
            RPN value (1-1000)
        """
        # Validate inputs
        if not all(1 <= x <= 10 for x in [gravity, occurrence, detection]):
            raise ValueError("All RPN components must be between 1 and 10")
        
        return gravity * occurrence * detection
    
    @staticmethod
    def get_risk_level(rpn_value: int) -> str:
        """
        Determine risk level based on RPN value.
        
        Classification:
        - Critical: RPN >= 200
        - High: 100 <= RPN < 200
        - Medium: 50 <= RPN < 100
        - Low: RPN < 50
        
        Args:
            rpn_value: Calculated RPN
        
        Returns:
            Risk level string
        """
        if rpn_value >= 200:
            return "critical"
        elif rpn_value >= 100:
            return "high"
        elif rpn_value >= 50:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    def create_rpn_analysis(
        db: Session,
        failure_mode_id: int,
        gravity: int,
        occurrence: int,
        detection: int,
        analyst_name: Optional[str] = None,
        comments: Optional[str] = None,
        corrective_action: Optional[str] = None,
        action_due_date: Optional[date] = None
    ) -> RPNAnalysis:
        """
        Create a new RPN analysis for a failure mode.
        
        Args:
            db: Database session
            failure_mode_id: ID of the failure mode
            gravity: Severity score (1-10)
            occurrence: Occurrence score (1-10)
            detection: Detection difficulty score (1-10)
            analyst_name: Name of analyst
            comments: Additional comments
            corrective_action: Proposed corrective action
            action_due_date: Due date for action
        
        Returns:
            Created RPNAnalysis object
        
        Raises:
            ValueError: If failure mode doesn't exist or inputs are invalid
        """
        # Verify failure mode exists
        failure_mode = db.query(FailureMode).filter(
            FailureMode.id == failure_mode_id
        ).first()
        
        if not failure_mode:
            raise ValueError(f"Failure mode with ID {failure_mode_id} not found")
        
        # Calculate RPN
        rpn_value = AMDECService.calculate_rpn(gravity, occurrence, detection)
        
        # Create analysis
        rpn_analysis = RPNAnalysis(
            failure_mode_id=failure_mode_id,
            gravity=gravity,
            occurrence=occurrence,
            detection=detection,
            rpn_value=rpn_value,
            analysis_date=date.today(),
            analyst_name=analyst_name,
            comments=comments,
            corrective_action=corrective_action,
            action_status="pending",
            action_due_date=action_due_date
        )
        
        db.add(rpn_analysis)
        db.commit()
        db.refresh(rpn_analysis)
        
        logger.info(
            f"Created RPN analysis: failure_mode_id={failure_mode_id}, "
            f"RPN={rpn_value} (G={gravity}, O={occurrence}, D={detection})"
        )
        
        return rpn_analysis
    
    @staticmethod
    def get_latest_rpn_for_failure_mode(
        db: Session,
        failure_mode_id: int
    ) -> Optional[RPNAnalysis]:
        """
        Get the most recent RPN analysis for a failure mode.
        
        Args:
            db: Database session
            failure_mode_id: ID of the failure mode
        
        Returns:
            Latest RPNAnalysis or None
        """
        return db.query(RPNAnalysis).filter(
            RPNAnalysis.failure_mode_id == failure_mode_id
        ).order_by(
            RPNAnalysis.analysis_date.desc(),
            RPNAnalysis.created_at.desc()
        ).first()
    
    @staticmethod
    def get_rpn_ranking(
        db: Session,
        equipment_id: Optional[int] = None,
        min_rpn: Optional[int] = None,
        risk_levels: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> Dict:
        """
        Get ranking of failure modes by RPN (highest risk first).
        Returns only the latest RPN analysis for each failure mode.
        
        Args:
            db: Database session
            equipment_id: Filter by specific equipment
            min_rpn: Minimum RPN threshold
            risk_levels: Filter by risk levels (critical, high, medium, low)
            limit: Maximum number of results
        
        Returns:
            Dict with ranking data and statistics
        """
        # Subquery to get latest RPN ID for each failure mode
        latest_rpn_id_subquery = db.query(
            func.max(RPNAnalysis.id).label('latest_id')
        ).group_by(
            RPNAnalysis.failure_mode_id
        ).subquery()
        
        # Main query with explicit joins
        query = db.query(
            FailureMode,
            RPNAnalysis,
            Equipment
        ).join(
            RPNAnalysis,
            FailureMode.id == RPNAnalysis.failure_mode_id
        ).join(
            Equipment,
            FailureMode.equipment_id == Equipment.id
        ).join(
            latest_rpn_id_subquery,
            RPNAnalysis.id == latest_rpn_id_subquery.c.latest_id
        ).filter(
            FailureMode.is_active == True
        )
        
        # Apply filters
        if equipment_id:
            query = query.filter(Equipment.id == equipment_id)
        
        if min_rpn:
            query = query.filter(RPNAnalysis.rpn_value >= min_rpn)
        
        # Order by RPN descending (highest risk first)
        query = query.order_by(RPNAnalysis.rpn_value.desc())
        
        results = query.all()
        
        # Build full result list and calculate stats
        ranking_all = []
        risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for failure_mode, rpn_analysis, equipment in results:
            risk_level = AMDECService.get_risk_level(rpn_analysis.rpn_value)
            
            # Apply risk level filter if specified
            if risk_levels and risk_level not in risk_levels:
                continue
            
            risk_counts[risk_level] += 1
            
            ranking_all.append({
                "failure_mode_id": failure_mode.id,
                "failure_mode_name": failure_mode.mode_name,
                "equipment_id": equipment.id,
                "equipment_designation": equipment.designation,
                "rpn_value": rpn_analysis.rpn_value,
                "gravity": rpn_analysis.gravity,
                "occurrence": rpn_analysis.occurrence,
                "detection": rpn_analysis.detection,
                "analysis_date": rpn_analysis.analysis_date,
                "corrective_action": rpn_analysis.corrective_action,
                "action_status": rpn_analysis.action_status,
                "risk_level": risk_level
            })
        
        # Apply limit to the ranking list after calculating stats on all matches
        total_matches = len(ranking_all)
        ranking_limited = ranking_all[:limit] if limit else ranking_all
        
        # Extract lightweight matrix data (G, O, RPN) for all matches
        matrix_data = [
            {
                "gravity": item["gravity"], 
                "occurrence": item["occurrence"],
                "rpn_value": item["rpn_value"]
            }
            for item in ranking_all
        ]
        
        return {
            "total_failure_modes": total_matches,
            "critical_count": risk_counts["critical"],
            "high_count": risk_counts["high"],
            "medium_count": risk_counts["medium"],
            "low_count": risk_counts["low"],
            "ranking": ranking_limited,
            "matrix_data": matrix_data,
            "generated_at": datetime.now()
        }
    
    @staticmethod
    def get_critical_equipment(
        db: Session,
        min_rpn: int = 200
    ) -> List[Dict]:
        """
        Get equipment with critical RPN values.
        
        Args:
            db: Database session
            min_rpn: Minimum RPN threshold (default: 200 for critical)
        
        Returns:
            List of equipment with their highest RPN values
        """
        # Subquery for latest RPN ID per failure mode
        latest_rpn_id_subquery = db.query(
            func.max(RPNAnalysis.id).label('latest_id')
        ).group_by(
            RPNAnalysis.failure_mode_id
        ).subquery()
        
        # Query to get max RPN per equipment
        query = db.query(
            Equipment.id,
            Equipment.designation,
            Equipment.type,
            Equipment.location,
            func.max(RPNAnalysis.rpn_value).label('max_rpn'),
            func.count(FailureMode.id).label('critical_failure_modes')
        ).join(
            FailureMode,
            Equipment.id == FailureMode.equipment_id
        ).join(
            RPNAnalysis,
            FailureMode.id == RPNAnalysis.failure_mode_id
        ).join(
            latest_rpn_id_subquery,
            RPNAnalysis.id == latest_rpn_id_subquery.c.latest_id
        ).filter(
            FailureMode.is_active == True,
            RPNAnalysis.rpn_value >= min_rpn
        ).group_by(
            Equipment.id,
            Equipment.designation,
            Equipment.type,
            Equipment.location
        ).order_by(
            func.max(RPNAnalysis.rpn_value).desc()
        )
        
        results = query.all()
        
        critical_equipment = []
        for result in results:
            critical_equipment.append({
                "equipment_id": result.id,
                "equipment_designation": result.designation,
                "equipment_type": result.type,
                "equipment_location": result.location,
                "max_rpn": result.max_rpn,
                "critical_failure_modes": result.critical_failure_modes,
                "risk_level": AMDECService.get_risk_level(result.max_rpn)
            })
        
        return critical_equipment
    
    @staticmethod
    def update_rpn_analysis(
        db: Session,
        rpn_analysis_id: int,
        gravity: Optional[int] = None,
        occurrence: Optional[int] = None,
        detection: Optional[int] = None,
        **kwargs
    ) -> RPNAnalysis:
        """
        Update an existing RPN analysis.
        Recalculates RPN if G, O, or D are updated.
        
        Args:
            db: Database session
            rpn_analysis_id: ID of the analysis to update
            gravity: New gravity score
            occurrence: New occurrence score
            detection: New detection score
            **kwargs: Other fields to update
        
        Returns:
            Updated RPNAnalysis object
        """
        rpn_analysis = db.query(RPNAnalysis).filter(
            RPNAnalysis.id == rpn_analysis_id
        ).first()
        
        if not rpn_analysis:
            raise ValueError(f"RPN analysis with ID {rpn_analysis_id} not found")
        
        # Update G, O, D if provided
        if gravity is not None:
            rpn_analysis.gravity = gravity
        if occurrence is not None:
            rpn_analysis.occurrence = occurrence
        if detection is not None:
            rpn_analysis.detection = detection
        
        # Recalculate RPN if any component changed
        if any(x is not None for x in [gravity, occurrence, detection]):
            rpn_analysis.rpn_value = AMDECService.calculate_rpn(
                rpn_analysis.gravity,
                rpn_analysis.occurrence,
                rpn_analysis.detection
            )
        
        # Update other fields
        for key, value in kwargs.items():
            if hasattr(rpn_analysis, key):
                setattr(rpn_analysis, key, value)
        
        db.commit()
        db.refresh(rpn_analysis)
        
    @staticmethod
    def generate_amdec_from_history(db: Session):
        """
        Automatically generate AMDEC/FMECA analysis from historical intervention data.
        
        Logic:
        1. Group interventions by Equipment and Failure Type (type_panne).
        2. Calculate Frequency (Occurrence):
           - Count interventions per failure mode
           - Normalize to 1-10 scale
        3. Calculate Severity (Gravity):
           - Average downtime (duree_arret)
           - Normalize to 1-10 scale
        4. Create or Update Failure Modes and RPN Analyses
        """
        from app.models import Intervention, Equipment
        
        # Get all closed/completed interventions with valid failure type
        results = db.query(
            Intervention.equipment_id,
            Intervention.type_panne,
            func.count(Intervention.id).label('frequency'),
            func.avg(Intervention.duree_arret).label('avg_downtime')
        ).filter(
            Intervention.type_panne.isnot(None),
            Intervention.equipment_id.isnot(None)
        ).group_by(
            Intervention.equipment_id,
            Intervention.type_panne
        ).all()
        
        generated_count = 0
        
        for r in results:
            if not r.type_panne or not r.equipment_id:
                continue
                
            # 1. Calculate Occurrence (Frequency)
            # Scale: 1 (rare) to 10 (very frequent)
            # Assumption: Max 20 failures/year is 10
            occurrence = min(10, max(1, int(r.frequency / 2))) 
            
            # 2. Calculate Gravity (Severity)
            # Scale: 1 (minor) to 10 (catastrophic)
            # Assumption: > 24h avg downtime is 10, < 1h is 1
            avg_hours = r.avg_downtime or 0
            gravity = min(10, max(1, int(avg_hours / 2)))
            
            # 3. Detection (Difficulty)
            # Default to 5 (Medium) as we can't infer this from raw data
            detection = 5
            
            # Find or Create Failure Mode
            failure_mode = db.query(FailureMode).filter(
                FailureMode.equipment_id == r.equipment_id,
                FailureMode.mode_name == r.type_panne
            ).first()
            
            if not failure_mode:
                failure_mode = FailureMode(
                    equipment_id=r.equipment_id,
                    mode_name=r.type_panne,
                    description=f"Auto-generated from history: {r.type_panne}",
                    failure_cause="Detected from historical interventions",
                    failure_effect="Operational downtime",
                    is_active=True
                )
                db.add(failure_mode)
                db.commit()
                db.refresh(failure_mode)
            
            # Create RPN Analysis
            AMDECService.create_rpn_analysis(
                db=db,
                failure_mode_id=failure_mode.id,
                gravity=gravity,
                occurrence=occurrence,
                detection=detection,
                analyst_name="System Auto-Analyzer",
                comments=f"Auto-calculated based on {r.frequency} interventions with avg downtime {avg_hours:.1f}h"
            )
            generated_count += 1
            
        return {"generated_count": generated_count}
