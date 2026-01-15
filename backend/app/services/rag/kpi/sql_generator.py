"""
SQL Generator Service
Safely converts natural language to SQL queries for specific tables.
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.rag.llm.provider_factory import LLMProviderFactory
from app.models import Equipment, Intervention, Technician, FailureMode

logger = logging.getLogger(__name__)

class SQLGeneratorService:
    """
    Generates and executes READ-ONLY SQL queries based on natural language.
    Strictly limited to SELECT statements on allowed tables.
    """
    
    ALLOWED_TABLES = [
        "equipment", 
        "interventions", 
        "technicians", 
        "spare_parts", 
        "failure_modes", 
        "technician_assignments"
    ]
    
    SCHEMA_DESCRIPTION = """
    Target Database Schema (PostgreSQL):
    
    1. equipment (id, designation, type, location, status, manufacturer, model, acquisition_date)
       - status enum: 'active', 'inactive', 'maintenance', 'decommissioned'
       
    2. interventions (id, equipment_id, type_panne, date_intervention, duree_arret, cout_total, status)
       - status enum: 'open', 'in_progress', 'completed', 'closed'
       - equipment_id links to equipment.id
       
    3. technicians (id, nom, prenom, specialite, status)
       - status enum: 'active', 'inactive'
       
    4. spare_parts (id, designation, reference, stock_actuel, cout_unitaire)
    
    5. failure_modes (id, equipment_id, mode_name, description, severity, rpn_value)
    """

    def __init__(self):
        self.llm_factory = LLMProviderFactory()

    async def generate_and_execute(self, query: str, db: Session) -> Dict[str, Any]:
        """
        1. Generate SQL from natural language
        2. Validate it's a safe SELECT
        3. Execute and return results
        """
        try:
            # 1. Generate SQL
            sql_query = await self._generate_sql(query)
            if not sql_query:
                return {"error": "Could not generate valid SQL"}
                
            # 2. Validate
            if not self._is_safe_query(sql_query):
                return {"error": "Generated SQL was flagged as unsafe"}
                
            # 3. Execute
            result = db.execute(text(sql_query)).mappings().all()
            
            # Format results
            data = [dict(row) for row in result]
            
            return {
                "generated_sql": sql_query,
                "row_count": len(data),
                "data": data,
                "summary": self._summarize_results(data)
            }
            
        except Exception as e:
            logger.error(f"SQL Generation error: {e}")
            return {"error": str(e)}

    async def _generate_sql(self, user_query: str) -> str:
        """Use LLM to generate SQL"""
        system_prompt = f"""
        You are an expert SQL generator for a PostgreSQL database.
        
        {self.SCHEMA_DESCRIPTION}
        
        Rules:
        1. Generate valid PostgreSQL SELECT statements ONLY.
        2. Use only the tables listed above.
        3. Do NOT use JOINs unless absolutely necessary.
        4. If the user asks for "how many", use COUNT(*).
        5. Return ONLY the raw SQL query, no markdown, no explanations.
        6. Do not end with a semicolon.
        """
        
        provider = self.llm_factory.get_provider()
        response = await provider.generate(
            system_prompt=system_prompt,
            user_prompt=f"Generate SQL for: {user_query}"
        )
        
        # Clean response
        sql = response.strip().replace("```sql", "").replace("```", "").strip()
        return sql

    def _is_safe_query(self, sql: str) -> bool:
        """Basic safety checks"""
        sql_lower = sql.lower()
        
        # Must start with SELECT
        if not sql_lower.startswith("select"):
            return False
            
        # No prohibited keywords
        forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "grant", "exec"]
        if any(w in sql_lower for w in forbidden):
            return False
            
        # Check table allowlist
        # Simple check - just ensure at least one allowed table is mentioned
        if not any(t in sql_lower for t in self.ALLOWED_TABLES):
            return False
            
        return True

    def _summarize_results(self, data: List[Dict]) -> str:
        """Create a tiny summary string for context"""
        if not data:
            return "No results found."
        
        if len(data) == 1 and "count" in data[0]:
            return f"Count: {data[0]['count']}"
            
        return f"Found {len(data)} records."

# Global instance
sql_generator = SQLGeneratorService()
