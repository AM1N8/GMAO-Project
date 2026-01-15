"""
Formation Priority Service - Business logic for Training Priority Score (TPS) calculation.

This service implements the TPS formula for prioritizing technician training
based on failure type (type_panne) analysis.

Academic Reference:
    Based on AMDEC (FMEA) methodology, extended with operational metrics.
    
Formula:
    TPS(type) = RPN_avg(type) × Failure_Frequency(type) × Failure_Difficulty(type) × Safety_Factor(type)

Components:
    - RPN_avg: Average RPN from AMDEC failure modes linked to this panne type
    - Failure_Frequency: Count of interventions in the analysis period
    - Failure_Difficulty: Ratio of problematic interventions (cancelled + delayed) / total
    - Safety_Factor: Domain-specific multiplier (electrical=1.5, hydraulic=1.3, etc.)

Deterministic Guarantees:
    - No AI/ML inference involved
    - No random elements
    - Fully reproducible with same input data
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from typing import Optional, List, Dict, Tuple
from datetime import date, datetime, timedelta
import logging
import numpy as np

from app.models import Intervention, FailureMode, RPNAnalysis, InterventionStatus

logger = logging.getLogger(__name__)


class FormationPriorityService:
    """
    Service for calculating Training Priority Scores (TPS) by panne type.
    
    All methods are static and stateless for testability and reproducibility.
    """
    
    # ==================== CONFIGURATION ====================
    
    # Percentile thresholds for priority classification
    HIGH_PERCENTILE_THRESHOLD = 90  # >= P90 = HIGH
    MEDIUM_PERCENTILE_THRESHOLD = 50  # >= P50 = MEDIUM, < P50 = LOW
    
    # Number of days an OPEN intervention is considered "delayed"
    DELAYED_THRESHOLD_DAYS = 7
    
    # Safety factors by panne type domain
    # Higher factor = higher risk = higher training priority
    SAFETY_FACTORS: Dict[str, float] = {
        # Safety/regulatory risk domains (factor = 1.5)
        "Électrique": 1.5,
        "Electrique": 1.5,
        "ELECTRIQUE": 1.5,
        "Electrical": 1.5,
        
        # Production stop risk domains (factor = 1.3)
        "Hydraulique": 1.3,
        "Hydraulic": 1.3,
        "Pneumatique": 1.3,
        "Pneumatic": 1.3,
        "Automate": 1.3,
        "PLC": 1.3,
        
        # Normal risk domains (factor = 1.0)
        "Mécanique": 1.0,
        "Mecanique": 1.0,
        "Mechanical": 1.0,
    }
    DEFAULT_SAFETY_FACTOR = 1.0
    
    # Training recommendations by domain
    TRAINING_RECOMMENDATIONS: Dict[str, str] = {
        "Électrique": "Formation maintenance électrique avancée - Habilitation",
        "Electrique": "Formation maintenance électrique avancée - Habilitation",
        "Hydraulique": "Formation systèmes hydrauliques industriels",
        "Pneumatique": "Formation systèmes pneumatiques",
        "Automate": "Formation programmation automates (PLC/API)",
        "PLC": "Formation programmation automates (PLC/API)",
        "Mécanique": "Formation mécanique industrielle",
        "Mecanique": "Formation mécanique industrielle",
    }
    DEFAULT_TRAINING = "Formation maintenance générale"
    
    # ==================== CORE CALCULATION ====================
    
    @staticmethod
    def calculate_tps_by_panne_type(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Calculate Training Priority Score (TPS) for each panne type.
        
        Algorithm:
        1. Aggregate interventions by type_panne within the date range
        2. For each type, calculate:
           - Frequency: count of interventions
           - Difficulty: (cancelled + delayed) / total
        3. Join with AMDEC to get average RPN per type
        4. Apply safety factor based on domain
        5. Calculate TPS = RPN_avg × Frequency × Difficulty × Safety_Factor
        6. Classify into priority levels using percentile thresholds
        
        Args:
            db: Database session
            start_date: Start of analysis period (defaults to 1 year ago)
            end_date: End of analysis period (defaults to today)
        
        Returns:
            Dict containing ranked priorities and metadata
        """
        # Default date range: last 12 months
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=365)
        
        logger.info(f"Calculating TPS for period {start_date} to {end_date}")
        
        # Step 1: Get intervention statistics by type_panne
        intervention_stats = FormationPriorityService._get_intervention_stats_by_type(
            db, start_date, end_date
        )
        
        if not intervention_stats:
            logger.warning("No interventions found in the specified period")
            return FormationPriorityService._build_empty_response(start_date, end_date)
        
        # Step 2: Get average RPN by type_panne from AMDEC
        rpn_averages = FormationPriorityService._get_rpn_average_by_type(db)
        
        # Step 3: Calculate TPS for each type
        tps_results = []
        
        for stat in intervention_stats:
            type_panne = stat["type_panne"]
            
            # Skip null/empty types
            if not type_panne or type_panne.strip() == "":
                continue
            
            # Get RPN average (default to 100 if no AMDEC data)
            rpn_avg = rpn_averages.get(type_panne, 100.0)
            
            # Get safety factor
            safety_factor = FormationPriorityService.SAFETY_FACTORS.get(
                type_panne, 
                FormationPriorityService.DEFAULT_SAFETY_FACTOR
            )
            
            # Calculate difficulty rate
            total = stat["total_count"]
            problematic = stat["cancelled_count"] + stat["delayed_count"]
            difficulty_rate = problematic / total if total > 0 else 0.0
            
            # Ensure minimum values to avoid zero TPS
            # Use at least 0.1 for difficulty if there are any interventions
            adjusted_difficulty = max(difficulty_rate, 0.1) if total > 0 else 0.1
            
            # Calculate TPS
            # Formula: RPN_avg × Frequency × Difficulty × Safety_Factor
            tps = rpn_avg * stat["total_count"] * adjusted_difficulty * safety_factor
            
            # Get training recommendation
            recommended_training = FormationPriorityService.TRAINING_RECOMMENDATIONS.get(
                type_panne,
                FormationPriorityService.DEFAULT_TRAINING
            )
            
            tps_results.append({
                "type_panne": type_panne,
                "training_priority_score": round(tps, 2),
                "rpn_average": round(rpn_avg, 2),
                "frequency": stat["total_count"],
                "difficulty_rate": round(difficulty_rate, 4),
                "safety_factor": safety_factor,
                "recommended_training": recommended_training,
                "failure_modes_count": rpn_averages.get(f"{type_panne}_count", 0),
                "total_interventions": total,
                "problematic_interventions": problematic
            })
        
        if not tps_results:
            return FormationPriorityService._build_empty_response(start_date, end_date)
        
        # Step 4: Classify priority levels using percentile thresholds
        tps_results = FormationPriorityService._classify_priorities(tps_results)
        
        # Step 5: Sort by TPS descending
        tps_results.sort(key=lambda x: x["training_priority_score"], reverse=True)
        
        # Build response
        high_count = sum(1 for r in tps_results if r["priority_level"] == "HIGH")
        medium_count = sum(1 for r in tps_results if r["priority_level"] == "MEDIUM")
        low_count = sum(1 for r in tps_results if r["priority_level"] == "LOW")
        
        return {
            "priorities": tps_results,
            "total_panne_types": len(tps_results),
            "high_priority_count": high_count,
            "medium_priority_count": medium_count,
            "low_priority_count": low_count,
            "period_start": start_date,
            "period_end": end_date,
            "generated_at": datetime.now(),
            "thresholds_used": {
                "high_percentile": FormationPriorityService.HIGH_PERCENTILE_THRESHOLD,
                "medium_percentile": FormationPriorityService.MEDIUM_PERCENTILE_THRESHOLD,
                "delayed_threshold_days": FormationPriorityService.DELAYED_THRESHOLD_DAYS
            }
        }
    
    # ==================== HELPER METHODS ====================
    
    @staticmethod
    def _get_intervention_stats_by_type(
        db: Session,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Aggregate intervention statistics by type_panne.
        
        Calculates:
        - Total count of interventions
        - Count of cancelled interventions
        - Count of delayed interventions (OPEN > threshold days)
        
        Uses a single optimized query to avoid N+1 issues.
        """
        # Calculate the delayed threshold date
        delayed_threshold_date = date.today() - timedelta(
            days=FormationPriorityService.DELAYED_THRESHOLD_DAYS
        )
        
        # Build aggregation query
        query = db.query(
            Intervention.type_panne,
            func.count(Intervention.id).label("total_count"),
            func.sum(
                case(
                    (Intervention.status == InterventionStatus.CANCELLED, 1),
                    else_=0
                )
            ).label("cancelled_count"),
            func.sum(
                case(
                    (
                        and_(
                            Intervention.status == InterventionStatus.OPEN,
                            Intervention.date_intervention < delayed_threshold_date
                        ),
                        1
                    ),
                    else_=0
                )
            ).label("delayed_count")
        ).filter(
            Intervention.type_panne.isnot(None),
            Intervention.date_intervention >= start_date,
            Intervention.date_intervention <= end_date
        ).group_by(
            Intervention.type_panne
        )
        
        results = query.all()
        
        return [
            {
                "type_panne": r.type_panne,
                "total_count": r.total_count or 0,
                "cancelled_count": r.cancelled_count or 0,
                "delayed_count": r.delayed_count or 0
            }
            for r in results
        ]
    
    @staticmethod
    def _get_rpn_average_by_type(db: Session) -> Dict[str, float]:
        """
        Get average RPN from AMDEC failure modes, grouped by mode_name (type_panne).
        
        Links:
        - FailureMode.mode_name corresponds to Intervention.type_panne
        - RPNAnalysis contains the RPN values for each failure mode
        
        Returns only the latest RPN analysis for each failure mode.
        """
        # Subquery to get latest RPN ID per failure mode
        latest_rpn_subquery = db.query(
            RPNAnalysis.failure_mode_id,
            func.max(RPNAnalysis.id).label("latest_id")
        ).group_by(
            RPNAnalysis.failure_mode_id
        ).subquery()
        
        # Main query: average RPN and count by mode_name
        query = db.query(
            FailureMode.mode_name,
            func.avg(RPNAnalysis.rpn_value).label("avg_rpn"),
            func.count(FailureMode.id).label("mode_count")
        ).join(
            RPNAnalysis,
            FailureMode.id == RPNAnalysis.failure_mode_id
        ).join(
            latest_rpn_subquery,
            RPNAnalysis.id == latest_rpn_subquery.c.latest_id
        ).filter(
            FailureMode.is_active == True
        ).group_by(
            FailureMode.mode_name
        )
        
        results = query.all()
        
        # Build lookup dictionary
        rpn_map = {}
        for r in results:
            if r.mode_name:
                rpn_map[r.mode_name] = float(r.avg_rpn) if r.avg_rpn else 100.0
                rpn_map[f"{r.mode_name}_count"] = r.mode_count or 0
        
        return rpn_map
    
    @staticmethod
    def _classify_priorities(tps_results: List[Dict]) -> List[Dict]:
        """
        Classify TPS values into priority levels using percentile thresholds.
        
        Classification:
        - HIGH: TPS >= P90 (top 10%)
        - MEDIUM: P50 <= TPS < P90 (above average)
        - LOW: TPS < P50 (below average)
        """
        if not tps_results:
            return tps_results
        
        # Extract TPS values
        tps_values = [r["training_priority_score"] for r in tps_results]
        
        # Calculate percentile thresholds
        p90 = float(np.percentile(tps_values, FormationPriorityService.HIGH_PERCENTILE_THRESHOLD))
        p50 = float(np.percentile(tps_values, FormationPriorityService.MEDIUM_PERCENTILE_THRESHOLD))
        
        # Classify each result
        for result in tps_results:
            tps = result["training_priority_score"]
            if tps >= p90:
                result["priority_level"] = "HIGH"
            elif tps >= p50:
                result["priority_level"] = "MEDIUM"
            else:
                result["priority_level"] = "LOW"
        
        return tps_results
    
    @staticmethod
    def _build_empty_response(start_date: date, end_date: date) -> Dict:
        """Build an empty response when no data is available."""
        return {
            "priorities": [],
            "total_panne_types": 0,
            "high_priority_count": 0,
            "medium_priority_count": 0,
            "low_priority_count": 0,
            "period_start": start_date,
            "period_end": end_date,
            "generated_at": datetime.now(),
            "thresholds_used": {
                "high_percentile": FormationPriorityService.HIGH_PERCENTILE_THRESHOLD,
                "medium_percentile": FormationPriorityService.MEDIUM_PERCENTILE_THRESHOLD,
                "delayed_threshold_days": FormationPriorityService.DELAYED_THRESHOLD_DAYS
            }
        }
    
    # ==================== NORMALIZATION (BONUS) ====================
    
    @staticmethod
    def normalize_tps_values(tps_results: List[Dict]) -> Dict:
        """
        Normalize TPS values to 0-100 scale for chart visualization.
        
        Uses min-max normalization:
            normalized = ((TPS - TPS_min) / (TPS_max - TPS_min)) * 100
        
        Args:
            tps_results: List of TPS result dictionaries
        
        Returns:
            Dict with normalized results and min/max values
        """
        if not tps_results:
            return {
                "priorities": [],
                "min_tps": 0,
                "max_tps": 0,
                "generated_at": datetime.now()
            }
        
        tps_values = [r["training_priority_score"] for r in tps_results]
        min_tps = min(tps_values)
        max_tps = max(tps_values)
        
        # Handle edge case where all values are the same
        tps_range = max_tps - min_tps
        if tps_range == 0:
            tps_range = 1  # Avoid division by zero
        
        normalized_results = []
        for r in tps_results:
            normalized_score = ((r["training_priority_score"] - min_tps) / tps_range) * 100
            normalized_results.append({
                "type_panne": r["type_panne"],
                "training_priority_score": r["training_priority_score"],
                "normalized_score": round(normalized_score, 2),
                "priority_level": r["priority_level"]
            })
        
        return {
            "priorities": normalized_results,
            "min_tps": round(min_tps, 2),
            "max_tps": round(max_tps, 2),
            "generated_at": datetime.now()
        }
    
    # ==================== COMPARISON (BONUS) ====================
    
    @staticmethod
    def compare_periods(
        db: Session,
        before_start: date,
        before_end: date,
        after_start: date,
        after_end: date
    ) -> Dict:
        """
        Compare TPS values between two periods to measure training effectiveness.
        
        Use Case:
            - Compare TPS before training program vs after training program
            - A decrease in TPS indicates improvement (fewer issues)
        
        Args:
            db: Database session
            before_start/before_end: The "before" period
            after_start/after_end: The "after" period
        
        Returns:
            Dict with comparison data for each panne type
        """
        # Calculate TPS for both periods
        before_result = FormationPriorityService.calculate_tps_by_panne_type(
            db, before_start, before_end
        )
        after_result = FormationPriorityService.calculate_tps_by_panne_type(
            db, after_start, after_end
        )
        
        # Build lookup for "before" values
        before_map = {
            r["type_panne"]: r 
            for r in before_result.get("priorities", [])
        }
        
        # Build comparisons
        comparisons = []
        for after_item in after_result.get("priorities", []):
            type_panne = after_item["type_panne"]
            before_item = before_map.get(type_panne)
            
            if before_item:
                tps_before = before_item["training_priority_score"]
                tps_after = after_item["training_priority_score"]
                tps_change = tps_after - tps_before
                tps_change_percent = (tps_change / tps_before * 100) if tps_before != 0 else 0
                
                comparisons.append({
                    "type_panne": type_panne,
                    "tps_before": tps_before,
                    "tps_after": tps_after,
                    "tps_change": round(tps_change, 2),
                    "tps_change_percent": round(tps_change_percent, 2),
                    "priority_before": before_item["priority_level"],
                    "priority_after": after_item["priority_level"],
                    "improved": tps_change < 0  # Lower TPS = improvement
                })
        
        total_improved = sum(1 for c in comparisons if c["improved"])
        total_degraded = sum(1 for c in comparisons if not c["improved"])
        
        return {
            "comparisons": comparisons,
            "period_before": {"start": before_start, "end": before_end},
            "period_after": {"start": after_start, "end": after_end},
            "total_improved": total_improved,
            "total_degraded": total_degraded,
            "generated_at": datetime.now()
        }
