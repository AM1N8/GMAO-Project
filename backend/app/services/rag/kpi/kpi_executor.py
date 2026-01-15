"""
KPI Executor
Bridges RAG queries to existing KPIService methods
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import date, timedelta
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.kpi_service import KPIService
from app.services.rag.router.entity_extractor import ExtractedEntities

logger = logging.getLogger(__name__)


@dataclass
class KPIResult:
    """Result from KPI execution"""
    kpi_type: str
    data: Dict[str, Any]
    formatted_context: str
    equipment_id: Optional[int] = None
    date_range: Optional[tuple] = None
    success: bool = True
    error: Optional[str] = None


class KPIExecutor:
    """
    Execute KPI queries using existing KPIService.
    
    This does NOT generate raw SQL - it calls the existing
    KPIService methods which have validated calculation logic.
    """
    
    # Mapping of detected KPI types to KPIService methods
    KPI_METHODS = {
        "mtbf": "calculate_mtbf",
        "mttr": "calculate_mttr", 
        "availability": "calculate_availability",
        "cost": "get_cost_breakdown",
        "dashboard": "get_dashboard_kpis",
        "trend": "calculate_mtbf",  # Default, will expand
        "count": "get_dashboard_kpis",  # Uses dashboard for counts
        "general_sql": "sql_generator", # Dynamic SQL
    }
    
    async def execute(
        self,
        kpi_type: str,
        entities: ExtractedEntities,
        db: Session,
        query_text: Optional[str] = None
    ) -> KPIResult:
        """
        Execute a KPI query.
        
        Args:
            kpi_type: Type of KPI (mtbf, mttr, availability, cost, etc.)
            entities: Extracted entities from query
            db: Database session
            query_text: Original query text (needed for SQL generation)
            
        Returns:
            KPIResult with data and formatted context
        """
        try:
            # Get equipment ID if available
            equipment_id = entities.equipment_ids[0] if entities.equipment_ids else None
            
            # Get date range (default to last 365 days if not specified)
            start_date, end_date = None, None
            is_default_range = False
            
            if entities.date_range:
                start_date, end_date = entities.date_range
            else:
                # DEFAULT: Last 365 days to avoid crashing on full table scans
                end_date = date.today()
                start_date = end_date - timedelta(days=365)
                is_default_range = True
            
            # Execute based on KPI type
            if kpi_type == "mtbf":
                data = KPIService.calculate_mtbf(
                    db, equipment_id, start_date, end_date
                )
                
            elif kpi_type == "mttr":
                data = KPIService.calculate_mttr(
                    db, equipment_id, start_date, end_date
                )
                
            elif kpi_type == "availability":
                data = KPIService.calculate_availability(
                    db, equipment_id, start_date, end_date
                )
                
            elif kpi_type == "cost":
                data = KPIService.get_cost_breakdown(
                    db, start_date, end_date, equipment_id
                )
                
            elif kpi_type == "dashboard":
                data = KPIService.get_dashboard_kpis(
                    db, start_date, end_date
                )
                
            elif kpi_type == "general_sql":
                # [NEW] Dynamic SQL Generation
                from app.services.rag.kpi.sql_generator import sql_generator
                
                if query_text:
                    sql_result = await sql_generator.generate_and_execute(query_text, db)
                    if "error" not in sql_result:
                        data = sql_result
                    else:
                        data = {"warnings": [sql_result["error"]]}
                else:
                     data = {"warnings": ["Query text missing for SQL generation"]}
                 
                
            else:
                # Default to dashboard for unknown types
                data = KPIService.get_dashboard_kpis(
                    db, start_date, end_date
                )
            
            # Format for LLM context
            formatted = self._format_for_context(kpi_type, data, equipment_id)
            
            # Add note about default date range if used
            if is_default_range:
                formatted += f"\n(Note: No date range specified, using last 365 days: {start_date} to {end_date})"
            
            return KPIResult(
                kpi_type=kpi_type,
                data=data,
                formatted_context=formatted,
                equipment_id=equipment_id,
                date_range=(start_date, end_date) if start_date else None,
                success=True
            )
            
        except Exception as e:
            logger.error(f"KPI execution error: {e}")
            return KPIResult(
                kpi_type=kpi_type,
                data={},
                formatted_context=f"Error calculating {kpi_type}: {str(e)}",
                success=False,
                error=str(e)
            )
    
    async def execute_multiple(
        self,
        kpi_types: List[str],
        entities: ExtractedEntities,
        db: Session
    ) -> List[KPIResult]:
        """Execute multiple KPI queries"""
        results = []
        for kpi_type in kpi_types:
            result = await self.execute(kpi_type, entities, db)
            results.append(result)
        return results
    
    def _format_for_context(
        self,
        kpi_type: str,
        data: Dict[str, Any],
        equipment_id: Optional[int]
    ) -> str:
        """Format KPI data as context for LLM"""
        
        lines = [f"=== KPI Data: {kpi_type.upper()} ==="]
        
        if equipment_id:
            lines.append(f"Equipment ID: {equipment_id}")
        
        if kpi_type == "mtbf":
            mtbf = data.get("mtbf_hours")
            if mtbf is not None:
                lines.append(f"MTBF (Mean Time Between Failures): {mtbf:.2f} hours")
            lines.append(f"Failure Count: {data.get('failure_count', 0)}")
            lines.append(f"Period: {data.get('period_start')} to {data.get('period_end')}")
            
        elif kpi_type == "mttr":
            mttr = data.get("mttr_hours")
            if mttr is not None:
                lines.append(f"MTTR (Mean Time To Repair): {mttr:.2f} hours")
            lines.append(f"Intervention Count: {data.get('intervention_count', 0)}")
            lines.append(f"Total Downtime: {data.get('total_downtime_hours', 0):.2f} hours")
            
        elif kpi_type == "availability":
            avail = data.get("availability_percentage")
            if avail is not None:
                lines.append(f"Availability: {avail:.2f}%")
            lines.append(f"Uptime: {data.get('uptime_hours', 0):.2f} hours")
            lines.append(f"Downtime: {data.get('downtime_hours', 0):.2f} hours")
            
        elif kpi_type == "cost":
            lines.append(f"Total Cost: €{data.get('total_cost', 0):.2f}")
            lines.append(f"Labor Cost: €{data.get('labor_cost', 0):.2f}")
            lines.append(f"Material Cost: €{data.get('material_cost', 0):.2f}")
            
        elif kpi_type == "dashboard":
            # Dashboard has multiple metrics
            if "mtbf" in data:
                lines.append(f"Fleet MTBF: {data['mtbf'].get('mtbf_hours', 'N/A')} hours")
            if "mttr" in data:
                lines.append(f"Fleet MTTR: {data['mttr'].get('mttr_hours', 'N/A')} hours")
            if "availability" in data:
                lines.append(f"Fleet Availability: {data['availability'].get('availability_percentage', 'N/A')}%")
            if "total_equipment" in data:
                lines.append(f"Total Equipment: {data['total_equipment']}")
            if "total_interventions" in data:
                lines.append(f"Total Interventions: {data['total_interventions']}")
        
        else:
            # Generic data dump
            for key, value in data.items():
                if not key.startswith("_"):
                    lines.append(f"{key}: {value}")
        
        # Add data quality warnings if present
        warnings = data.get("warnings", [])
        if warnings:
            lines.append("\nData Quality Warnings:")
            for warning in warnings[:3]:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)
    
    def get_available_kpis(self) -> List[str]:
        """Get list of available KPI types"""
        return list(self.KPI_METHODS.keys())


# Global instance
kpi_executor = KPIExecutor()
