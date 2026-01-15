"""
Entity Extractor
Extracts equipment, dates, and other entities from queries
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntities:
    """Entities extracted from a query"""
    equipment_names: List[str]
    equipment_ids: List[int]
    date_range: Optional[Tuple[date, date]]
    component_names: List[str]
    part_numbers: List[str]
    technician_names: List[str]
    raw_numbers: List[float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "equipment_names": self.equipment_names,
            "equipment_ids": self.equipment_ids,
            "date_range": [str(d) for d in self.date_range] if self.date_range else None,
            "component_names": self.component_names,
            "part_numbers": self.part_numbers,
            "technician_names": self.technician_names,
            "raw_numbers": self.raw_numbers
        }


class EntityExtractor:
    """
    Extract entities from queries for routing and context.
    
    Extracts:
    - Equipment names/IDs
    - Date ranges
    - Component names
    - Part numbers
    """
    
    # Common date patterns
    DATE_PATTERNS = [
        # Relative: "last month", "this year"
        (r"last (\d+)? ?(day|week|month|year)s?", "relative"),
        (r"this (week|month|quarter|year)", "relative_this"),
        (r"depuis (\d+) (jour|semaine|mois|an)s?", "relative_fr"),
        
        # Absolute: "2024-01-15", "15/01/2024"
        (r"(\d{4})-(\d{2})-(\d{2})", "iso"),
        (r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", "dmy"),
        
        # Named: "January 2024", "Q1 2024"
        (r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})", "month_year"),
        (r"Q([1-4])\s+(\d{4})", "quarter"),
    ]
    
    # Equipment code patterns
    EQUIPMENT_PATTERNS = [
        r"(?:equipment|équipement|machine|pump|pompe|motor|moteur)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-_]+)",
        r"\b([A-Z]{2,4}[-_]?\d{2,5})\b",  # Equipment codes like "PMP-001"
    ]
    
    def __init__(self):
        self._equipment_cache: Dict[str, int] = {}  # name -> id cache
    
    async def extract(
        self,
        query: str,
        db: Optional[Session] = None
    ) -> ExtractedEntities:
        """
        Extract all entities from a query.
        
        Args:
            query: User query text
            db: Optional database session for entity resolution
            
        Returns:
            ExtractedEntities with all extracted information
        """
        query_lower = query.lower()
        
        # Extract equipment
        equipment_names, equipment_ids = await self._extract_equipment(query, db)
        
        # Extract date range
        date_range = self._extract_date_range(query_lower)
        
        # Extract components
        component_names = self._extract_components(query)
        
        # Extract part numbers
        part_numbers = self._extract_part_numbers(query)
        
        # Extract technician names
        technician_names = await self._extract_technicians(query, db)
        
        # Extract raw numbers
        raw_numbers = self._extract_numbers(query)
        
        return ExtractedEntities(
            equipment_names=equipment_names,
            equipment_ids=equipment_ids,
            date_range=date_range,
            component_names=component_names,
            part_numbers=part_numbers,
            technician_names=technician_names,
            raw_numbers=raw_numbers
        )
    
    async def _extract_equipment(
        self,
        query: str,
        db: Optional[Session]
    ) -> Tuple[List[str], List[int]]:
        """Extract equipment references"""
        names = []
        ids = []
        
        # Pattern matching
        for pattern in self.EQUIPMENT_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                name = match if isinstance(match, str) else match[0]
                if name and len(name) > 2:
                    names.append(name)
        
        # Resolve to IDs if database available
        if db and names:
            try:
                from app.models import Equipment
                
                for name in names:
                    # Check cache first
                    if name in self._equipment_cache:
                        ids.append(self._equipment_cache[name])
                        continue
                    
                    # Query database
                    eq = db.query(Equipment).filter(
                        (Equipment.designation.ilike(f"%{name}%")) |
                        (Equipment.code.ilike(f"%{name}%") if hasattr(Equipment, 'code') else False)
                    ).first()
                    
                    if eq:
                        self._equipment_cache[name] = eq.id
                        ids.append(eq.id)
                        
            except Exception as e:
                logger.debug(f"Error resolving equipment: {e}")
        
        return list(set(names)), list(set(ids))
    
    def _extract_date_range(
        self,
        query: str
    ) -> Optional[Tuple[date, date]]:
        """Extract date range from query"""
        today = date.today()
        
        # Check relative patterns
        # "last N months/weeks/days"
        match = re.search(r"last (\d+)?\s*(day|week|month|year)s?", query)
        if match:
            count = int(match.group(1)) if match.group(1) else 1
            unit = match.group(2)
            
            if unit == "day":
                start = today - timedelta(days=count)
            elif unit == "week":
                start = today - timedelta(weeks=count)
            elif unit == "month":
                start = today - timedelta(days=count * 30)
            elif unit == "year":
                start = today - timedelta(days=count * 365)
            else:
                start = today - timedelta(days=30)
            
            return (start, today)
        
        # "this month/year"
        match = re.search(r"this (week|month|quarter|year)", query)
        if match:
            unit = match.group(1)
            
            if unit == "week":
                start = today - timedelta(days=today.weekday())
            elif unit == "month":
                start = today.replace(day=1)
            elif unit == "quarter":
                quarter_month = ((today.month - 1) // 3) * 3 + 1
                start = today.replace(month=quarter_month, day=1)
            elif unit == "year":
                start = today.replace(month=1, day=1)
            else:
                start = today.replace(day=1)
            
            return (start, today)
        
        # ISO date pattern
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})", query)
        if match:
            try:
                extracted_date = date(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3))
                )
                # Single date - assume from that date to today
                return (extracted_date, today)
            except ValueError:
                pass
        
        return None
    
    def _extract_components(self, query: str) -> List[str]:
        """Extract component mentions"""
        components = []
        
        # Common component patterns
        patterns = [
            r"(?:component|composant|part|pièce)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-_\s]+)",
            r"(?:seal|joint|bearing|roulement|valve|motor|pump|sensor)\s*([A-Z0-9\-]+)?",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 2:
                    components.append(match.strip())
        
        return list(set(components))
    
    def _extract_part_numbers(self, query: str) -> List[str]:
        """Extract part numbers"""
        patterns = [
            r"(?:part|pièce|ref|référence|p/n|pn)[:\s#]*([A-Z0-9][-A-Z0-9]{3,20})",
        ]
        
        parts = []
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            parts.extend(matches)
        
        return list(set(parts))
    
    async def _extract_technicians(
        self,
        query: str,
        db: Optional[Session]
    ) -> List[str]:
        """Extract technician references"""
        technicians = []
        
        if db:
            try:
                from app.models import Technician
                
                # Get all technician names
                all_techs = db.query(Technician.name).all()
                for (name,) in all_techs:
                    if name and name.lower() in query.lower():
                        technicians.append(name)
            except Exception as e:
                logger.debug(f"Error extracting technicians: {e}")
        
        return technicians
    
    def _extract_numbers(self, query: str) -> List[float]:
        """Extract raw numbers from query"""
        pattern = r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:hours?|heures?|days?|jours?|€|EUR|%)?(?!\d)"
        matches = re.findall(pattern, query)
        
        return [float(m) for m in matches if m]


# Global instance
entity_extractor = EntityExtractor()
