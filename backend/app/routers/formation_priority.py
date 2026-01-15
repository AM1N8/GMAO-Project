"""
Formation Priority Router - API endpoints for Training Priority by Panne Type.

This router exposes the Formation Priority module's functionality via REST endpoints,
enabling maintenance managers to access TPS (Training Priority Score) analysis.

Endpoints:
    GET /by-panne-type     - Calculate TPS for all panne types
    GET /by-panne-type/normalized - Get normalized TPS values (0-100) for charts
    GET /compare           - Compare TPS between two periods (before/after training)

Academic Notes:
    All endpoints are deterministic and reproducible.
    The TPS formula is based on AMDEC (FMEA) methodology.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.services.formation_priority_service import FormationPriorityService
from app.schemas import (
    FormationPriorityResponse,
    FormationPriorityNormalizedResponse,
    FormationPriorityComparisonResponse
)

router = APIRouter()


@router.get(
    "/by-panne-type",
    response_model=FormationPriorityResponse,
    summary="Calculate Training Priority by Panne Type",
    description="""
    Calculate Training Priority Score (TPS) for each failure type (type_panne).
    
    **Formula:**
    ```
    TPS(type) = RPN_avg × Failure_Frequency × Failure_Difficulty × Safety_Factor
    ```
    
    **Components:**
    - **RPN_avg**: Average Risk Priority Number from AMDEC failure modes
    - **Failure_Frequency**: Count of interventions in the analysis period
    - **Failure_Difficulty**: Ratio of problematic interventions (cancelled + delayed > 7 days)
    - **Safety_Factor**: Domain-specific multiplier (Electrical=1.5, Hydraulic=1.3, etc.)
    
    **Priority Classification (Percentile-based):**
    - **HIGH**: TPS >= 90th percentile (top 10% most critical)
    - **MEDIUM**: TPS >= 50th percentile (above average)
    - **LOW**: TPS < 50th percentile (below average)
    
    **Use Cases:**
    - Prioritize technician training programs
    - Identify most problematic failure domains
    - Allocate training budget effectively
    - Support maintenance strategy decisions
    """
)
def get_formation_priority_by_panne_type(
    start_date: Optional[date] = Query(
        None, 
        description="Start of analysis period (defaults to 12 months ago)"
    ),
    end_date: Optional[date] = Query(
        None, 
        description="End of analysis period (defaults to today)"
    ),
    db: Session = Depends(get_db)
):
    """
    Calculate TPS for all panne types within the specified date range.
    
    Returns a ranked list of panne types with their TPS scores,
    priority levels, and contributing metrics.
    """
    try:
        result = FormationPriorityService.calculate_tps_by_panne_type(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating formation priority: {str(e)}"
        )


@router.get(
    "/by-panne-type/normalized",
    response_model=FormationPriorityNormalizedResponse,
    summary="Get Normalized TPS Values for Charts",
    description="""
    Get TPS values normalized to 0-100 scale for dashboard visualization.
    
    **Normalization Formula:**
    ```
    normalized_score = ((TPS - TPS_min) / (TPS_max - TPS_min)) × 100
    ```
    
    **Use Cases:**
    - Bar chart visualization on dashboard
    - Progress indicators
    - Relative comparison between panne types
    """
)
def get_normalized_formation_priority(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get normalized TPS values for chart visualization.
    
    The normalization scales all TPS values to 0-100 range,
    making them suitable for bar charts and progress indicators.
    """
    try:
        # First calculate raw TPS
        raw_result = FormationPriorityService.calculate_tps_by_panne_type(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
        
        # Then normalize
        normalized_result = FormationPriorityService.normalize_tps_values(
            raw_result.get("priorities", [])
        )
        
        return normalized_result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error normalizing formation priority: {str(e)}"
        )


@router.get(
    "/compare",
    response_model=FormationPriorityComparisonResponse,
    summary="Compare TPS Between Two Periods",
    description="""
    Compare Training Priority Scores between two periods to measure training effectiveness.
    
    **Use Cases:**
    - Evaluate training program impact
    - Before/after analysis for specific domains
    - Track improvement trends over time
    
    **Interpretation:**
    - **Negative TPS change**: Improvement (fewer/easier interventions)
    - **Positive TPS change**: Degradation (more/harder interventions)
    
    **Example:**
    Compare Q1 2025 (before training) vs Q2 2025 (after training) to see
    if the electrical maintenance training reduced electrical failures.
    """
)
def compare_formation_priority_periods(
    before_start: date = Query(..., description="Start date of 'before' period"),
    before_end: date = Query(..., description="End date of 'before' period"),
    after_start: date = Query(..., description="Start date of 'after' period"),
    after_end: date = Query(..., description="End date of 'after' period"),
    db: Session = Depends(get_db)
):
    """
    Compare TPS values between two periods.
    
    This endpoint helps evaluate training effectiveness by comparing
    TPS before and after training programs.
    """
    # Validate date ranges
    if before_start > before_end:
        raise HTTPException(
            status_code=400,
            detail="before_start must be before or equal to before_end"
        )
    
    if after_start > after_end:
        raise HTTPException(
            status_code=400,
            detail="after_start must be before or equal to after_end"
        )
    
    if before_end >= after_start:
        raise HTTPException(
            status_code=400,
            detail="'Before' period must end before 'after' period starts"
        )
    
    try:
        result = FormationPriorityService.compare_periods(
            db=db,
            before_start=before_start,
            before_end=before_end,
            after_start=after_start,
            after_end=after_end
        )
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing periods: {str(e)}"
        )


@router.get(
    "/health",
    summary="Formation Priority Health Check",
    description="Check if the formation priority service is operational."
)
def formation_priority_health():
    """Health check endpoint for the formation priority module."""
    return {
        "status": "healthy",
        "service": "FormationPriorityService",
        "version": "1.0.0",
        "available_endpoints": [
            "GET /by-panne-type",
            "GET /by-panne-type/normalized",
            "GET /compare"
        ]
    }
