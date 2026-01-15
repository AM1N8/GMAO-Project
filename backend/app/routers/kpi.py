"""
KPI router - Provides endpoints for maintenance analytics and KPIs.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange

from app.database import get_db
from app.services.kpi_service import KPIService
from app.schemas import (
    MTBFResponse, MTTRResponse, AvailabilityResponse,
    DashboardKPIs
)
from app.models import Equipment

router = APIRouter()


@router.get("/dashboard", response_model=DashboardKPIs)
def get_dashboard_kpis(
    start_date: Optional[date] = Query(None, description="Start date for KPI calculation"),
    end_date: Optional[date] = Query(None, description="End date for KPI calculation (defaults to today)"),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard KPIs in a single request."""
    return KPIService.get_dashboard_kpis(db, start_date, end_date)


@router.get("/mtbf", response_model=MTBFResponse)
def calculate_mtbf(
    equipment_id: Optional[int] = Query(None, description="Filter by specific equipment"),
    start_date: Optional[date] = Query(None, description="Start date for calculation"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    db: Session = Depends(get_db)
):
    """Calculate Mean Time Between Failures (MTBF)."""
    return KPIService.calculate_mtbf(db, equipment_id, start_date, end_date)


@router.get("/mttr", response_model=MTTRResponse)
def calculate_mttr(
    equipment_id: Optional[int] = Query(None, description="Filter by specific equipment"),
    start_date: Optional[date] = Query(None, description="Start date for calculation"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    db: Session = Depends(get_db)
):
    """Calculate Mean Time To Repair (MTTR)."""
    return KPIService.calculate_mttr(db, equipment_id, start_date, end_date)


@router.get("/availability", response_model=AvailabilityResponse)
def calculate_availability(
    equipment_id: Optional[int] = Query(None, description="Filter by specific equipment"),
    start_date: Optional[date] = Query(None, description="Start date for calculation"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    db: Session = Depends(get_db)
):
    """Calculate Equipment Availability percentage."""
    return KPIService.calculate_availability(db, equipment_id, start_date, end_date)


@router.get("/monthly-equipment-kpis")
def get_monthly_equipment_kpis(
    equipment_id: Optional[int] = Query(None, description="Filter by specific equipment (omit for all)"),
    start_date: Optional[date] = Query(None, description="Start date (defaults to 12 months ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    operational_hours_per_day: float = Query(24.0, ge=1, le=24, description="Operational hours per day"),
    operational_days_per_week: int = Query(7, ge=1, le=7, description="Operational days per week"),
    db: Session = Depends(get_db)
):
    """
    Get monthly MTBF, MTTR, and Availability for each equipment.
    
    **Returns:**
    - Monthly breakdown of all three KPIs per equipment
    - Aggregated totals per equipment
    - Overall fleet summary
    
    **Use cases:**
    - Track equipment performance trends over time
    - Identify seasonal patterns in failures
    - Compare equipment reliability month-over-month
    - Generate monthly maintenance reports
    """
    # Set default date range
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - relativedelta(months=12)
    
    # Get equipment list
    eq_query = db.query(Equipment)
    if equipment_id:
        eq_query = eq_query.filter(Equipment.id == equipment_id)
    equipment_list = eq_query.filter(Equipment.status == 'active').all()
    
    if not equipment_list:
        raise HTTPException(status_code=404, detail="No equipment found")
    
    # Generate list of months in the date range
    months = []
    current = date(start_date.year, start_date.month, 1)
    end_month = date(end_date.year, end_date.month, 1)
    
    while current <= end_month:
        last_day = monthrange(current.year, current.month)[1]
        month_end = min(date(current.year, current.month, last_day), end_date)
        month_start = max(current, start_date)
        
        months.append({
            "year": current.year,
            "month": current.month,
            "month_name": current.strftime("%B %Y"),
            "start_date": month_start,
            "end_date": month_end
        })
        current += relativedelta(months=1)
    
    # Calculate KPIs for each equipment and month
    equipment_results = []
    
    for eq in equipment_list:
        monthly_data = []
        total_failures = 0
        total_downtime = 0
        total_interventions = 0
        
        for month in months:
            # Calculate MTBF for this month
            mtbf_result = KPIService.calculate_mtbf(
                db, eq.id, month["start_date"], month["end_date"],
                operational_hours_per_day
            )
            
            # Calculate MTTR for this month
            mttr_result = KPIService.calculate_mttr(
                db, eq.id, month["start_date"], month["end_date"]
            )
            
            # Calculate Availability for this month
            avail_result = KPIService.calculate_availability(
                db, eq.id, month["start_date"], month["end_date"],
                operational_hours_per_day, operational_days_per_week
            )
            
            # Accumulate totals
            total_failures += mtbf_result.get("failure_count", 0)
            total_downtime += mttr_result.get("total_downtime_hours", 0) or 0
            total_interventions += mttr_result.get("intervention_count", 0)
            
            monthly_data.append({
                "year": month["year"],
                "month": month["month"],
                "month_name": month["month_name"],
                "mtbf_hours": mtbf_result.get("mtbf_hours"),
                "mttr_hours": mttr_result.get("mttr_hours"),
                "availability_percentage": avail_result.get("availability_percentage"),
                "failure_count": mtbf_result.get("failure_count", 0),
                "intervention_count": mttr_result.get("intervention_count", 0),
                "downtime_hours": avail_result.get("downtime_hours", 0),
                "uptime_hours": avail_result.get("uptime_hours", 0)
            })
        
        # Calculate overall KPIs for this equipment
        overall_mtbf = KPIService.calculate_mtbf(
            db, eq.id, start_date, end_date, operational_hours_per_day
        )
        overall_mttr = KPIService.calculate_mttr(db, eq.id, start_date, end_date)
        overall_avail = KPIService.calculate_availability(
            db, eq.id, start_date, end_date,
            operational_hours_per_day, operational_days_per_week
        )
        
        equipment_results.append({
            "equipment_id": eq.id,
            "equipment_designation": eq.designation,
            "equipment_code": getattr(eq, 'code', None),
            "monthly_kpis": monthly_data,
            "period_summary": {
                "mtbf_hours": overall_mtbf.get("mtbf_hours"),
                "mttr_hours": overall_mttr.get("mttr_hours"),
                "availability_percentage": overall_avail.get("availability_percentage"),
                "total_failures": total_failures,
                "total_interventions": total_interventions,
                "total_downtime_hours": round(total_downtime, 2)
            }
        })
    
    # Calculate fleet-wide summary
    fleet_mtbf = KPIService.calculate_mtbf(db, None, start_date, end_date, operational_hours_per_day)
    fleet_mttr = KPIService.calculate_mttr(db, None, start_date, end_date)
    fleet_avail = KPIService.calculate_availability(
        db, None, start_date, end_date,
        operational_hours_per_day, operational_days_per_week
    )
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "months_count": len(months)
        },
        "operational_schedule": {
            "hours_per_day": operational_hours_per_day,
            "days_per_week": operational_days_per_week
        },
        "fleet_summary": {
            "equipment_count": len(equipment_list),
            "mtbf_hours": fleet_mtbf.get("mtbf_hours"),
            "mttr_hours": fleet_mttr.get("mttr_hours"),
            "availability_percentage": fleet_avail.get("availability_percentage"),
            "total_failures": fleet_mtbf.get("failure_count", 0),
            "total_interventions": fleet_mttr.get("intervention_count", 0)
        },
        "equipment_data": equipment_results
    }


@router.get("/failure-rate")
def get_failure_distribution(
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    equipment_id: Optional[int] = Query(None, description="Filter by equipment"),
    db: Session = Depends(get_db)
):
    """Get failure type distribution with statistics."""
    return KPIService.get_failure_distribution(db, start_date, end_date, equipment_id)


@router.get("/cost-analysis")
def get_cost_breakdown(
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    equipment_id: Optional[int] = Query(None, description="Filter by equipment"),
    db: Session = Depends(get_db)
):
    """Get maintenance cost breakdown and analysis."""
    return KPIService.get_cost_breakdown(db, start_date, end_date, equipment_id)


@router.get("/trends")
def get_kpi_trends(
    metric: str = Query(..., pattern="^(mtbf|mttr|availability|cost|failures)$"),
    equipment_id: Optional[int] = Query(None, description="Filter by equipment"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    granularity: str = Query("month", pattern="^(week|month|quarter|year)$"),
    db: Session = Depends(get_db)
):
    """Get KPI trends over time with specified granularity."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365)
    
    data_points = []
    current_date = start_date
    
    while current_date < end_date:
        # Determine interval end
        if granularity == "week":
            interval_end = current_date + timedelta(weeks=1)
            label = current_date.strftime("%Y-W%U")
        elif granularity == "month":
            interval_end = current_date + relativedelta(months=1)
            label = current_date.strftime("%Y-%m")
        elif granularity == "quarter":
            interval_end = current_date + relativedelta(months=3)
            label = f"{current_date.year}-Q{(current_date.month-1)//3 + 1}"
        elif granularity == "year":
            interval_end = current_date + relativedelta(years=1)
            label = str(current_date.year)
        else:
            interval_end = end_date
            label = "Total"
            
        # Cap at end_date of query
        if interval_end > end_date:
            interval_end = end_date
            
        # Skip if start >= end (sanity check)
        if current_date >= interval_end:
            break
            
        # Calculate metric for this specific interval
        if metric == "mtbf":
            result = KPIService.calculate_mtbf(db, equipment_id, current_date, interval_end)
            data_points.append({
                "period": label,
                "start_date": current_date,
                "value": result.get("mtbf_hours"),
                "failure_count": result.get("failure_count")
            })
        elif metric == "mttr":
            result = KPIService.calculate_mttr(db, equipment_id, current_date, interval_end)
            data_points.append({
                "period": label,
                "start_date": current_date,
                "value": result.get("mttr_hours"),
                "intervention_count": result.get("intervention_count")
            })
        elif metric == "availability":
            result = KPIService.calculate_availability(db, equipment_id, current_date, interval_end)
            data_points.append({
                "period": label,
                "start_date": current_date,
                "value": result.get("availability_percentage"),
                "uptime_hours": result.get("uptime_hours"),
                "downtime_hours": result.get("downtime_hours")
            })
        elif metric == "cost":
            result = KPIService.get_cost_breakdown(db, current_date, interval_end, equipment_id)
            data_points.append({
                "period": label,
                "start_date": current_date,
                "value": result.get("total_cost"), 
                "material_cost": result.get("material_cost"),
                "labor_cost": result.get("labor_cost")
            })
        elif metric == "failures":
             # Special case for raw failure counts (useful for 'maintenance activity' trend)
             dist = KPIService.get_failure_distribution(db, current_date, interval_end, equipment_id)
             total = sum(d['count'] for d in dist)
             data_points.append({
                 "period": label,
                 "start_date": current_date,
                 "value": total,
                 "details": dist
             })

        # Advance current_date
        current_date = interval_end
    
    return {
        "metric": metric, 
        "granularity": granularity, 
        "equipment_id": equipment_id, 
        "period": {"start_date": start_date, "end_date": end_date}, 
        "data_points": data_points
    }


@router.get("/comparison")
def compare_equipment_kpis(
    equipment_ids: str = Query(..., description="Comma-separated equipment IDs (e.g., '1,2,3')"),
    metric: str = Query("availability", pattern="^(mtbf|mttr|availability|cost)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Compare KPIs across multiple equipment."""
    try:
        eq_ids = [int(id.strip()) for id in equipment_ids.split(',')]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid equipment IDs format")
    
    comparisons = []
    for eq_id in eq_ids:
        equipment = db.query(Equipment).filter(Equipment.id == eq_id).first()
        if not equipment:
            continue
        
        if metric == "mtbf":
            result = KPIService.calculate_mtbf(db, eq_id, start_date, end_date)
            value = result.get("mtbf_hours")
        elif metric == "mttr":
            result = KPIService.calculate_mttr(db, eq_id, start_date, end_date)
            value = result.get("mttr_hours")
        elif metric == "availability":
            result = KPIService.calculate_availability(db, eq_id, start_date, end_date)
            value = result.get("availability_percentage")
        else:
            result = KPIService.get_cost_breakdown(db, start_date, end_date, eq_id)
            value = result.get("total_cost")
        
        comparisons.append({"equipment_id": eq_id, "equipment_designation": equipment.designation, "metric_value": value, "details": result})
    
    comparisons.sort(key=lambda x: x["metric_value"] or 0, reverse=(metric != "mttr"))
    return {"metric": metric, "period": {"start_date": start_date, "end_date": end_date}, "comparisons": comparisons}