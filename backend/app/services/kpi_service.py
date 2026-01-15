"""
KPI Service - Business logic for calculating maintenance KPIs.
Provides methods for MTBF, MTTR, Availability, and other analytics.

CORRECTED VERSION - Fixes:
1. MTBF: Now calculates actual time between consecutive failures
2. Availability: Bounds checking, configurable operational hours
3. Enhanced error handling and data validation
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Tuple
from enum import Enum
import logging

from app.models import Equipment, Intervention, InterventionPart, TechnicianAssignment

logger = logging.getLogger(__name__)


class AvailabilityMethod(Enum):
    """Methods for calculating availability"""
    HOURLY = "hourly"  # Based on operational hours
    DAILY = "daily"    # Based on operational days


class KPIService:
    """Service class for KPI calculations"""
    
    # Default operational assumptions
    DEFAULT_HOURS_PER_DAY = 24
    DEFAULT_DAYS_PER_WEEK = 7
    
    @staticmethod
    def _validate_date_range(
        start_date: Optional[date],
        end_date: Optional[date]
    ) -> Tuple[bool, List[str]]:
        """Validate date range and return warnings"""
        warnings = []
        
        if start_date and end_date:
            if start_date > end_date:
                warnings.append("Start date is after end date - dates will be swapped")
            if end_date > date.today():
                warnings.append("End date is in the future - using today's date")
        
        return len(warnings) == 0, warnings
    
    @staticmethod
    def _normalize_date_range(
        start_date: Optional[date],
        end_date: Optional[date]
    ) -> Tuple[Optional[date], Optional[date]]:
        """Normalize and fix date range issues"""
        if start_date and end_date and start_date > end_date:
            start_date, end_date = end_date, start_date
        
        if end_date and end_date > date.today():
            end_date = date.today()
        
        return start_date, end_date
    
    @staticmethod
    def _get_corrective_interventions_query(
        db: Session,
        equipment_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ):
        """Build base query for corrective interventions (failures only)"""
        query = db.query(Intervention)
        
        if equipment_id:
            query = query.filter(Intervention.equipment_id == equipment_id)
        
        if start_date:
            query = query.filter(Intervention.date_intervention >= start_date)
        
        if end_date:
            query = query.filter(Intervention.date_intervention <= end_date)
        
        # Exclude preventive maintenance
        query = query.filter(
            Intervention.type_panne.notin_(['Préventif', 'Preventive', 'preventive', 'PREVENTIVE'])
        )
        
        return query
    
    @staticmethod
    def calculate_mtbf(
        db: Session,
        equipment_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        operational_hours_per_day: float = 24.0
    ) -> Dict:
        """
        Calculate Mean Time Between Failures (MTBF)
        
        CORRECT Formula: Sum of time intervals between consecutive failures / (N - 1)
        where N is the number of failures.
        
        This measures the ACTUAL average operating time between failures,
        not total calendar time divided by failure count.
        
        Args:
            db: Database session
            equipment_id: Filter by specific equipment
            start_date: Start of period
            end_date: End of period
            operational_hours_per_day: Hours equipment operates per day (default: 24)
        
        Returns:
            Dict with MTBF hours, intervals, failure count, and warnings
        """
        warnings = []
        
        try:
            # Validate and normalize dates
            _, date_warnings = KPIService._validate_date_range(start_date, end_date)
            warnings.extend(date_warnings)
            start_date, end_date = KPIService._normalize_date_range(start_date, end_date)
            
            # Validate operational hours
            if operational_hours_per_day <= 0 or operational_hours_per_day > 24:
                warnings.append(f"Invalid operational_hours_per_day ({operational_hours_per_day}), using 24")
                operational_hours_per_day = 24.0
            
            # Validate equipment exists if specified
            if equipment_id:
                equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
                if not equipment:
                    return {
                        "mtbf_hours": None,
                        "total_operating_hours": 0,
                        "failure_count": 0,
                        "time_intervals": [],
                        "equipment_id": equipment_id,
                        "period_start": start_date,
                        "period_end": end_date,
                        "calculation_method": "between_failures",
                        "data_quality_warnings": ["Equipment not found"]
                    }
            
            # Get failures ordered by date
            query = KPIService._get_corrective_interventions_query(
                db, equipment_id, start_date, end_date
            )
            interventions = query.order_by(Intervention.date_intervention.asc()).all()
            
            failure_count = len(interventions)
            
            # MTBF requires at least 2 failures to calculate time BETWEEN them
            if failure_count < 2:
                msg = "Insufficient failures for MTBF calculation (need at least 2)"
                if failure_count == 1:
                    msg = "Only 1 failure recorded - cannot calculate time between failures"
                elif failure_count == 0:
                    msg = "No failures recorded in period"
                
                return {
                    "mtbf_hours": None,
                    "total_operating_hours": 0,
                    "failure_count": failure_count,
                    "time_intervals": [],
                    "equipment_id": equipment_id,
                    "period_start": start_date,
                    "period_end": end_date,
                    "calculation_method": "between_failures",
                    "operational_hours_per_day": operational_hours_per_day,
                    "data_quality_warnings": [msg]
                }
            
            # Calculate time intervals between consecutive failures
            time_intervals = []
            total_interval_hours = 0
            
            for i in range(1, len(interventions)):
                prev_failure = interventions[i - 1]
                curr_failure = interventions[i]
                
                # Calculate calendar days between failures
                days_between = (curr_failure.date_intervention - prev_failure.date_intervention).days
                
                # Convert to operational hours
                hours_between = days_between * operational_hours_per_day
                
                # Subtract repair time of previous failure (equipment was down)
                prev_repair_time = prev_failure.duree_arret or 0
                adjusted_hours = max(0, hours_between - prev_repair_time)
                
                time_intervals.append({
                    "from_date": prev_failure.date_intervention.isoformat(),
                    "to_date": curr_failure.date_intervention.isoformat(),
                    "calendar_days": days_between,
                    "operational_hours": round(adjusted_hours, 2)
                })
                
                total_interval_hours += adjusted_hours
            
            # MTBF = Sum of intervals / (Number of failures - 1)
            mtbf = total_interval_hours / (failure_count - 1)
            
            # Sanity check
            if mtbf < 0:
                warnings.append("Calculated negative MTBF - check data quality")
                mtbf = 0
            
            return {
                "mtbf_hours": round(mtbf, 2),
                "total_operating_hours": round(total_interval_hours, 2),
                "failure_count": failure_count,
                "intervals_calculated": failure_count - 1,
                "time_intervals": time_intervals,
                "equipment_id": equipment_id,
                "period_start": start_date,
                "period_end": end_date,
                "calculation_method": "between_failures",
                "operational_hours_per_day": operational_hours_per_day,
                "data_quality_warnings": warnings if warnings else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating MTBF: {e}")
            raise
    
    @staticmethod
    def calculate_mttr(
        db: Session,
        equipment_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Calculate Mean Time To Repair (MTTR)
        
        Formula: Sum of Repair Durations / Number of Repairs
        
        Args:
            db: Database session
            equipment_id: Filter by specific equipment
            start_date: Start of period
            end_date: End of period
        
        Returns:
            Dict with MTTR hours, total downtime, intervention count, and warnings
        """
        warnings = []
        
        try:
            # Validate and normalize dates
            _, date_warnings = KPIService._validate_date_range(start_date, end_date)
            warnings.extend(date_warnings)
            start_date, end_date = KPIService._normalize_date_range(start_date, end_date)
            
            # Validate equipment exists if specified
            if equipment_id:
                equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
                if not equipment:
                    return {
                        "mttr_hours": None,
                        "total_downtime_hours": 0,
                        "intervention_count": 0,
                        "equipment_id": equipment_id,
                        "period_start": start_date,
                        "period_end": end_date,
                        "data_quality_warnings": ["Equipment not found"]
                    }
            
            # Build query
            query = KPIService._get_corrective_interventions_query(
                db, equipment_id, start_date, end_date
            )
            
            # Get individual interventions for validation
            interventions = query.all()
            
            if not interventions:
                return {
                    "mttr_hours": None,
                    "total_downtime_hours": 0,
                    "intervention_count": 0,
                    "min_repair_time": None,
                    "max_repair_time": None,
                    "equipment_id": equipment_id,
                    "period_start": start_date,
                    "period_end": end_date,
                    "data_quality_warnings": ["No interventions found in period"]
                }
            
            # Calculate with validation
            repair_times = []
            invalid_count = 0
            
            for intervention in interventions:
                repair_time = intervention.duree_arret
                
                if repair_time is None:
                    invalid_count += 1
                    continue
                
                if repair_time < 0:
                    warnings.append(f"Negative repair time found (ID: {intervention.id})")
                    invalid_count += 1
                    continue
                
                # Flag unusually long repairs (> 30 days)
                if repair_time > 720:
                    warnings.append(
                        f"Unusually long repair time: {repair_time}h (ID: {intervention.id})"
                    )
                
                repair_times.append(repair_time)
            
            if invalid_count > 0:
                warnings.append(f"{invalid_count} interventions excluded due to invalid repair times")
            
            if not repair_times:
                return {
                    "mttr_hours": None,
                    "total_downtime_hours": 0,
                    "intervention_count": 0,
                    "valid_interventions": 0,
                    "equipment_id": equipment_id,
                    "period_start": start_date,
                    "period_end": end_date,
                    "data_quality_warnings": warnings + ["No valid repair times found"]
                }
            
            total_downtime = sum(repair_times)
            intervention_count = len(repair_times)
            mttr = total_downtime / intervention_count
            
            return {
                "mttr_hours": round(mttr, 2),
                "total_downtime_hours": round(total_downtime, 2),
                "intervention_count": len(interventions),
                "valid_interventions": intervention_count,
                "min_repair_time": round(min(repair_times), 2),
                "max_repair_time": round(max(repair_times), 2),
                "median_repair_time": round(sorted(repair_times)[len(repair_times)//2], 2),
                "equipment_id": equipment_id,
                "period_start": start_date,
                "period_end": end_date,
                "data_quality_warnings": warnings if warnings else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating MTTR: {e}")
            raise
    
    @staticmethod
    def calculate_availability(
        db: Session,
        equipment_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        operational_hours_per_day: float = 24.0,
        operational_days_per_week: int = 7,
        method: AvailabilityMethod = AvailabilityMethod.HOURLY
    ) -> Dict:
        """
        Calculate Equipment Availability with bounds checking
        
        Formula: ((Total Operational Time - Downtime) / Total Operational Time) × 100
        
        FIXES:
        - Bounds checking ensures result is always 0-100%
        - Configurable operational schedule
        - Two calculation methods available
        
        Args:
            db: Database session
            equipment_id: Filter by specific equipment
            start_date: Start of period
            end_date: End of period
            operational_hours_per_day: Hours per day equipment operates (1-24)
            operational_days_per_week: Days per week equipment operates (1-7)
            method: Calculation method (HOURLY or DAILY)
        
        Returns:
            Dict with availability percentage (always 0-100) and breakdown
        """
        warnings = []
        
        try:
            # Validate and normalize dates
            _, date_warnings = KPIService._validate_date_range(start_date, end_date)
            warnings.extend(date_warnings)
            start_date, end_date = KPIService._normalize_date_range(start_date, end_date)
            
            # Validate operational parameters
            if operational_hours_per_day <= 0 or operational_hours_per_day > 24:
                warnings.append(
                    f"Invalid operational_hours_per_day ({operational_hours_per_day}), using 24"
                )
                operational_hours_per_day = 24.0
            
            if operational_days_per_week <= 0 or operational_days_per_week > 7:
                warnings.append(
                    f"Invalid operational_days_per_week ({operational_days_per_week}), using 7"
                )
                operational_days_per_week = 7
            
            # Validate equipment exists if specified
            equipment = None
            if equipment_id:
                equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
                if not equipment:
                    return {
                        "availability_percentage": None,
                        "total_hours": 0,
                        "downtime_hours": 0,
                        "uptime_hours": 0,
                        "equipment_id": equipment_id,
                        "period_start": start_date,
                        "period_end": end_date,
                        "calculation_method": method.value,
                        "data_quality_warnings": ["Equipment not found"]
                    }
            
            # Build query for all interventions (including preventive for downtime)
            query = db.query(Intervention)
            
            if equipment_id:
                query = query.filter(Intervention.equipment_id == equipment_id)
            
            if start_date:
                query = query.filter(Intervention.date_intervention >= start_date)
            
            if end_date:
                query = query.filter(Intervention.date_intervention <= end_date)
            
            interventions = query.all()
            
            # Determine analysis period
            if equipment_id and equipment:
                period_start = start_date or (
                    equipment.acquisition_date if equipment.acquisition_date 
                    else (interventions[0].date_intervention if interventions else date.today())
                )
            else:
                period_start = start_date or (
                    min(i.date_intervention for i in interventions) if interventions 
                    else date.today()
                )
            
            period_end = end_date or date.today()
            
            # Calculate total operational hours based on schedule
            total_calendar_days = (period_end - period_start).days
            if total_calendar_days <= 0:
                total_calendar_days = 1  # Minimum 1 day
            
            # Calculate operational days (accounting for days per week)
            weeks = total_calendar_days / 7
            operational_days = weeks * operational_days_per_week
            
            # Total operational hours
            equipment_count = 1
            if not equipment_id:
                 # For fleet analysis, total time = time * number of active equipment
                equipment_count = db.query(Equipment).filter(Equipment.status == 'active').count() or 1

            total_operational_hours = operational_days * operational_hours_per_day * equipment_count
            
            if total_operational_hours <= 0:
                total_operational_hours = operational_hours_per_day  # Minimum
            
            # Calculate downtime with validation
            downtime_hours = 0
            for intervention in interventions:
                repair_time = intervention.duree_arret or 0
                
                if repair_time < 0:
                    warnings.append(f"Negative downtime ignored (ID: {intervention.id})")
                    continue
                
                downtime_hours += repair_time
            
            # CRITICAL FIX: Bounds checking
            # Downtime cannot exceed total operational time
            if downtime_hours > total_operational_hours:
                warnings.append(
                    f"Downtime ({downtime_hours:.2f}h) exceeds operational time "
                    f"({total_operational_hours:.2f}h) - capping at 100% downtime"
                )
                downtime_hours = total_operational_hours
            
            # Calculate uptime
            uptime_hours = total_operational_hours - downtime_hours
            
            # Calculate availability (guaranteed 0-100%)
            availability = (uptime_hours / total_operational_hours) * 100
            
            # Final bounds check (should be unnecessary but defensive)
            availability = max(0.0, min(100.0, availability))
            
            return {
                "availability_percentage": round(availability, 2),
                "total_hours": round(total_operational_hours, 2),
                "total_calendar_days": total_calendar_days,
                "operational_days": round(operational_days, 2),
                "downtime_hours": round(downtime_hours, 2),
                "uptime_hours": round(uptime_hours, 2),
                "intervention_count": len(interventions),
                "equipment_id": equipment_id,
                "period_start": period_start,
                "period_end": period_end,
                "calculation_method": method.value,
                "operational_hours_per_day": operational_hours_per_day,
                "operational_days_per_week": operational_days_per_week,
                "data_quality_warnings": warnings if warnings else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating availability: {e}")
            raise
    
    @staticmethod
    def get_failure_distribution(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        equipment_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get failure type distribution with counts and percentages
        
        Args:
            db: Database session
            start_date: Start of period
            end_date: End of period
            equipment_id: Filter by specific equipment
        
        Returns:
            List of dicts with failure type statistics
        """
        try:
            start_date, end_date = KPIService._normalize_date_range(start_date, end_date)
            
            query = db.query(
                Intervention.type_panne,
                func.count(Intervention.id).label('count'),
                func.sum(Intervention.duree_arret).label('total_downtime'),
                func.avg(Intervention.duree_arret).label('avg_downtime')
            )
            
            if equipment_id:
                query = query.filter(Intervention.equipment_id == equipment_id)
            
            if start_date:
                query = query.filter(Intervention.date_intervention >= start_date)
            
            if end_date:
                query = query.filter(Intervention.date_intervention <= end_date)
            
            query = query.filter(Intervention.type_panne.isnot(None))
            query = query.group_by(Intervention.type_panne)
            query = query.order_by(func.count(Intervention.id).desc())
            
            results = query.all()
            total_count = sum(r.count for r in results)
            
            distribution = []
            for result in results:
                percentage = (result.count / total_count * 100) if total_count > 0 else 0
                distribution.append({
                    "type_panne": result.type_panne,
                    "count": result.count,
                    "percentage": round(percentage, 2),
                    "total_downtime": round(result.total_downtime or 0, 2),
                    "average_downtime": round(result.avg_downtime or 0, 2)
                })
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting failure distribution: {e}")
            raise
    
    @staticmethod
    def get_cost_breakdown(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        equipment_id: Optional[int] = None
    ) -> Dict:
        """Get cost breakdown: material vs labor"""
        try:
            start_date, end_date = KPIService._normalize_date_range(start_date, end_date)
            
            query = db.query(
                func.sum(Intervention.cout_total).label('total_cost'),
                func.sum(Intervention.cout_materiel).label('material_cost'),
                func.sum(Intervention.cout_main_oeuvre).label('labor_cost'),
                func.count(Intervention.id).label('intervention_count')
            )
            
            if equipment_id:
                query = query.filter(Intervention.equipment_id == equipment_id)
            if start_date:
                query = query.filter(Intervention.date_intervention >= start_date)
            if end_date:
                query = query.filter(Intervention.date_intervention <= end_date)
            
            result = query.first()
            
            total_cost = result.total_cost or 0
            material_cost = result.material_cost or 0
            labor_cost = result.labor_cost or 0
            
            material_pct = (material_cost / total_cost * 100) if total_cost > 0 else 0
            labor_pct = (labor_cost / total_cost * 100) if total_cost > 0 else 0
            
            return {
                "total_cost": round(total_cost, 2),
                "material_cost": round(material_cost, 2),
                "labor_cost": round(labor_cost, 2),
                "material_percentage": round(material_pct, 2),
                "labor_percentage": round(labor_pct, 2),
                "intervention_count": result.intervention_count or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting cost breakdown: {e}")
            raise
    
    @staticmethod
    def get_dashboard_kpis(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        operational_hours_per_day: float = 24.0,
        operational_days_per_week: int = 7
    ) -> Dict:
        """
        Get comprehensive dashboard KPIs in one call
        
        Args:
            db: Database session
            start_date: Start of period
            end_date: End of period
            operational_hours_per_day: Hours per day equipment operates
            operational_days_per_week: Days per week equipment operates
        
        Returns:
            Dict with all KPIs for dashboard
        """
        try:
            mtbf = KPIService.calculate_mtbf(
                db, None, start_date, end_date, operational_hours_per_day
            )
            mttr = KPIService.calculate_mttr(db, None, start_date, end_date)
            availability = KPIService.calculate_availability(
                db, None, start_date, end_date,
                operational_hours_per_day, operational_days_per_week
            )
            cost_breakdown = KPIService.get_cost_breakdown(db, start_date, end_date)
            failure_distribution = KPIService.get_failure_distribution(db, start_date, end_date)
            
            equipment_count = db.query(func.count(Equipment.id)).filter(
                Equipment.status == 'active'
            ).scalar()
            
            from app.models import Technician, TechnicianStatus
            technician_count = db.query(func.count(Technician.id)).filter(
                Technician.status == TechnicianStatus.ACTIVE
            ).scalar()
            
            intervention_query = db.query(Intervention)
            if start_date:
                intervention_query = intervention_query.filter(
                    Intervention.date_intervention >= start_date
                )
            if end_date:
                intervention_query = intervention_query.filter(
                    Intervention.date_intervention <= end_date
                )
            
            total_interventions = intervention_query.count()
            open_interventions = intervention_query.filter(
                Intervention.status.in_(['open', 'in_progress'])
            ).count()
            
            # Collect all warnings
            all_warnings = []
            for kpi in [mtbf, mttr, availability]:
                if kpi.get('data_quality_warnings'):
                    all_warnings.extend(kpi['data_quality_warnings'])
            
            return {
                "mtbf": mtbf,
                "mttr": mttr,
                "availability": availability,
                "cost_breakdown": cost_breakdown,
                "failure_distribution": failure_distribution,
                "total_interventions": total_interventions,
                "open_interventions": open_interventions,
                "equipment_count": equipment_count or 0,
                "technician_count": technician_count or 0,
                "period_start": start_date,
                "period_end": end_date,
                "operational_schedule": {
                    "hours_per_day": operational_hours_per_day,
                    "days_per_week": operational_days_per_week
                },
                "data_quality_warnings": all_warnings if all_warnings else None
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard KPIs: {e}")
            raise