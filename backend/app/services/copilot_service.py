"""
Maintenance Copilot Service
Handles AI-assisted engineering tasks: KPI explanation, health summaries, and reports.
"""

import json
import logging
import re
from typing import Optional, Dict, List, Any
from datetime import date, datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
from fastapi import HTTPException

from app.services.rag.llm_service import llm_service
from app.services.kpi_service import KPIService
from app.services.amdec_service import AMDECService
from app.models import Equipment, Intervention, FailureMode, RPNAnalysis
from app.schemas import (
    CopilotIntentEnum, 
    CopilotQueryRequest, 
    CopilotQueryResponse,
    CopilotRecommendedAction, 
    CopilotSupportingData,
    CopilotContext
)

logger = logging.getLogger(__name__)


class CopilotService:
    """
    Service for the Maintenance Copilot.
    Orchestrates data retrieval and LLM reasoning to provide engineering insights.
    """

    async def process_query(self, db: Session, request: CopilotQueryRequest) -> CopilotQueryResponse:
        """
        Main entry point for Copilot queries.
        1. Detects intent
        2. Routes to specific handler
        3. Formats response
        """
        # 1. Detect Intent
        intent = await self._detect_intent(request.message)
        logger.info(f"Detected intent '{intent}' for query: {request.message}")

        # 2. Enrich Context (Entity Extraction)
        try:
            # If no equipment_id is provided, try to extract it from natural language
            if request.context is None:
                request.context = CopilotContext()
                
            if not request.context.equipment_id:
                extracted_eq = await self._extract_entity(request.message, "EQUIPMENT")
                if extracted_eq:
                    # Validate against DB safely
                    filters = [Equipment.designation.ilike(f"%{extracted_eq}%")]
                    if extracted_eq.isdigit():
                        filters.append(Equipment.id == int(extracted_eq))
                    
                    eq = db.query(Equipment).filter(or_(*filters)).first()
                    
                    if eq:
                        request.context.equipment_id = str(eq.id)
                        logger.info(f"Extracted and resolved equipment: {eq.designation} (ID: {eq.id})")
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            # Continue without context enrichment

        # 3. Route to Handler
        if intent == CopilotIntentEnum.KPI_EXPLANATION:
            return await self._handle_kpi_explanation(db, request)
        elif intent == CopilotIntentEnum.EQUIPMENT_HEALTH_SUMMARY:
            return await self._handle_equipment_health(db, request)
        elif intent == CopilotIntentEnum.INTERVENTION_REPORT:
            return await self._handle_intervention_report(db, request)
        else:
            # Fallback
            return await self._handle_kpi_explanation(db, request)

    async def _extract_entity(self, message: str, entity_type: str) -> Optional[str]:
        """
        Extract specific entity type from message using LLM.
        """
        prompt = f"""
        Extract the {entity_type} name or ID from this user query.
        User Query: "{message}"
        
        Return ONLY the extracted value. If found, return just the value.
        If NO {entity_type} is mentioned, return "None".
        Do not add quotes or labels.
        """
        try:
            response = await llm_service.generate_simple(prompt)
            cleaned = response.strip().replace('"', '').replace("'", "")
            if "None" in cleaned or len(cleaned) < 1:
                return None
            return cleaned
        except Exception:
            return None

    async def _detect_intent(self, message: str) -> CopilotIntentEnum:
        """
        Use LLM to classify user intent into one of the supported enums.
        """
        prompt = f"""
        You are a classification system for a maintenance assistant.
        Classify the following user query into one of these intents:

        1. KPI_EXPLANATION: Questions about metrics (MTTR, MTBF, Availability), trends, statistics, or performance analysis.
        2. EQUIPMENT_HEALTH_SUMMARY: Questions about the overall status, health, or risk level of a machine/equipment.
        3. INTERVENTION_REPORT: Requests to generate a report, summary, or details about a specific maintenance intervention or work order.

        User Query: "{message}"

        Return ONLY the Enum value (KPI_EXPLANATION, EQUIPMENT_HEALTH_SUMMARY, or INTERVENTION_REPORT). Do not add any text.
        """
        try:
            response_text = await llm_service.generate_simple(prompt)
            cleaned_response = response_text.strip().replace('"', '').replace("'", "").upper()
            
            # Match against enum
            if "KPI" in cleaned_response:
                return CopilotIntentEnum.KPI_EXPLANATION
            elif "HEALTH" in cleaned_response or "STATUS" in cleaned_response:
                return CopilotIntentEnum.EQUIPMENT_HEALTH_SUMMARY
            elif "REPORT" in cleaned_response or "INTERVENTION" in cleaned_response:
                return CopilotIntentEnum.INTERVENTION_REPORT
            
            return CopilotIntentEnum.KPI_EXPLANATION # Default
            
        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            return CopilotIntentEnum.KPI_EXPLANATION

    async def _handle_kpi_explanation(self, db: Session, request: CopilotQueryRequest) -> CopilotQueryResponse:
        """
        Handle KPI explanation requests.
        Retrieves KPIS for context and asks LLM to explain.
        """
        # Extract context
        equipment_id = None
        if request.context and request.context.equipment_id:
            # Try to resolve equipment ID from string or int
            eq_id_str = str(request.context.equipment_id)
            if eq_id_str.isdigit():
                 equipment_id = int(eq_id_str)
            else:
                # Resolve by designation
                eq = db.query(Equipment).filter(Equipment.designation == eq_id_str).first()
                if eq:
                    equipment_id = eq.id

        # Fetch Data
        kpis = KPIService.get_dashboard_kpis(db, operational_hours_per_day=24) # Simplified for now
        
        # If specific equipment, get specific KPIs
        mtbf_data = None
        mttr_data = None
        
        if equipment_id:
            mtbf_data = KPIService.calculate_mtbf(db, equipment_id=equipment_id)
            mttr_data = KPIService.calculate_mttr(db, equipment_id=equipment_id)
            context_data = {
                "global_kpis": kpis,
                "specific_mtbf": mtbf_data,
                "specific_mttr": mttr_data
            }
        else:
            context_data = {"global_kpis": kpis}

        # Prepare Prompt
        prompt = f"""
        You are a Maintenance Engineering Copilot. 
        Analyze the following KPI data and answer the user's question.
        
        User Question: "{request.message}"
        
        Data Context:
        {json.dumps(context_data, default=str)}
        
        Instructions:
        1. Explain the relevant KPIs (MTTR, MTBF, Availability).
        2. Identify any trends (high MTTR = long repairs, low MTBF = frequent failures).
        3. Suggest 2-3 corrective actions based on the data.
        
        Response Format (JSON):
        STRICT JSON ONLY. No markdown, no preamble. Escape all quotes.
        {{
            "summary": "Brief overview (1-2 sentences)",
            "detailed_explanation": "Detailed analysis...",
            "recommended_actions": [
                {{"action": "Action 1", "priority": "high", "rationale": "Why..."}}
            ],
            "confidence_level": "high"
        }}
        """
        
        try:
            llm_response = await llm_service.generate_simple(prompt)
            # JSON parsing logic
            response_data = self._parse_json_response(llm_response)
            
            # Construct Supporting Data
            supporting = []
            if equipment_id:
                 supporting.append(CopilotSupportingData(
                     data_type="kpi", 
                     description=f"MTBF for Equipment {equipment_id}", 
                     value=f"{mtbf_data.get('mtbf_hours', 'N/A')}h"
                 ))
            
            return CopilotQueryResponse(
                intent=CopilotIntentEnum.KPI_EXPLANATION,
                summary=response_data.get("summary", "Analysis complete."),
                detailed_explanation=response_data.get("detailed_explanation", llm_response),
                recommended_actions=self._sanitize_recommended_actions(response_data.get("recommended_actions", [])),
                supporting_data_references=supporting,
                confidence_level=response_data.get("confidence_level", "medium").lower()
            )
            
        except Exception as e:
            logger.error(f"KPI handling failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to process KPI explanation")

    async def _handle_equipment_health(self, db: Session, request: CopilotQueryRequest) -> CopilotQueryResponse:
        """
        Handle Equipment Health Summary requests.
        Aggregates Equipment info, KPIs, Critical RPNs.
        """
        equipment_id = None
        if request.context and request.context.equipment_id:
             eq_id_str = str(request.context.equipment_id)
             if eq_id_str.isdigit():
                 equipment_id = int(eq_id_str)
             else:
                eq = db.query(Equipment).filter(Equipment.designation == eq_id_str).first()
                if eq:
                    equipment_id = eq.id
        
        if not equipment_id:
             # Check for "highest risk" or "critical" intent in the message
             if any(kw in request.message.lower() for kw in ["risk", "critical", "danger", "worst", "bad"]):
                 # Resolve by finding equipment with max RPN
                 top_risk = db.query(RPNAnalysis).order_by(desc(RPNAnalysis.rpn_value)).first()
                 if top_risk:
                     # Get the associated failure mode -> equipment
                     # (Assuming RPNAnalysis -> FailureMode -> Equipment from schema knowledge, 
                     # but let's check schema. RPNAnalysis -> failure_mode_id. FailureMode -> equipment_id)
                     fm = db.query(FailureMode).filter(FailureMode.id == top_risk.failure_mode_id).first()
                     if fm:
                         equipment_id = fm.equipment_id
                         logger.info(f"Resolved 'highest risk' query to Equipment ID: {equipment_id}")
            
             if not equipment_id:
                 # Still no equipment found
                 return CopilotQueryResponse(
                     intent=CopilotIntentEnum.EQUIPMENT_HEALTH_SUMMARY,
                     summary="No equipment specified.",
                     detailed_explanation="Please specify an equipment ID or designation, or ask about 'highest risk' equipment.",
                     confidence_level="low"
                 )

        # 1. Get Equipment Details
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        
        # 2. Get KPIs
        mtbf = KPIService.calculate_mtbf(db, equipment_id=equipment_id)
        availability = KPIService.calculate_availability(db, equipment_id=equipment_id)
        
        # 3. Get Critical AMDEC/RPN
        # We can reuse get_critical_equipment or query directly
        # Let's get top RPNs for this equipment
        rpn_ranking = AMDECService.get_rpn_ranking(db, equipment_id=equipment_id, limit=3)
        
        # 4. Get Open Interventions
        open_interventions = db.query(Intervention).filter(
            Intervention.equipment_id == equipment_id,
            Intervention.status.in_(['open', 'in_progress'])
        ).count()

        health_data = {
            "equipment": {
                "name": equipment.designation,
                "status": equipment.status.value,
                "age_years": (date.today().year - equipment.acquisition_date.year) if equipment.acquisition_date else None
            },
            "kpis": {
                "mtbf_hours": mtbf.get('mtbf_hours'),
                "availability": availability.get('availability_percentage')
            },
            "risk_analysis": {
                "critical_failure_modes_count": rpn_ranking.get('critical_count', 0),
                "top_risks": rpn_ranking.get('ranking', [])
            },
            "maintenance_backlog": open_interventions
        }

        # Prompt LLM
        prompt = f"""
        You are a Reliability Engineer. Assess the health of this equipment.

        Equipment Data:
        {json.dumps(health_data, default=str)}

        Instructions:
        1. Determine overall status: "Healthy", "At Risk", or "Critical".
        2. Justify based on availability, MTBF trends, and critical risks (RPN).
        3. Recommend immediate actions if At Risk or Critical.

        Response Format (JSON):
        STRICT JSON ONLY. No markdown, no preamble. Escape all quotes.
        {{
            "summary": "Equipment is [Status] due to...",
            "detailed_explanation": "Full assessment...",
            "recommended_actions": [ ... ],
            "confidence_level": "high"
        }}
        """

        try:
            llm_response = await llm_service.generate_simple(prompt)
            data = self._parse_json_response(llm_response)
            
            supporting = [
                CopilotSupportingData(data_type="kpi", description="Availability", value=f"{availability.get('availability_percentage')}%"),
                CopilotSupportingData(data_type="amdec", description="Critical Failure Modes", value=str(rpn_ranking.get('critical_count', 0))),
                CopilotSupportingData(data_type="intervention", description="Open Interventions", value=str(open_interventions))
            ]

            return CopilotQueryResponse(
                intent=CopilotIntentEnum.EQUIPMENT_HEALTH_SUMMARY,
                summary=data.get("summary", "Health assessment complete."),
                detailed_explanation=data.get("detailed_explanation", llm_response),
                recommended_actions=self._sanitize_recommended_actions(data.get("recommended_actions", [])),
                supporting_data_references=supporting,
                confidence_level=data.get("confidence_level", "high").lower()
            )
        except Exception as e:
            logger.error(f"Health summary failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate health summary")

    async def _handle_intervention_report(self, db: Session, request: CopilotQueryRequest) -> CopilotQueryResponse:
        """
        Handle Intervention Report generation.
        """
        intervention_id = request.context.intervention_id if request.context else None
        
        if not intervention_id:
            # Try to resolve by searching (Date, Description)
            # Use LLM to extract search params
            search_params = await self._extract_intervention_search_params(request.message)
            logger.info(f"Extracted search params: {search_params}")
            
            query = db.query(Intervention)
            if search_params.get("date"):
                try:
                    query = query.filter(Intervention.date_intervention == search_params["date"])
                except Exception:
                    pass # Invalid date format
            
            if search_params.get("keywords"):
                 kw = search_params["keywords"]
                 # Search in type, category, or equipment designation
                 query = query.join(Equipment).filter(
                     or_(
                         Intervention.type_panne.ilike(f"%{kw}%"),
                         Intervention.categorie_panne.ilike(f"%{kw}%"),
                         Equipment.designation.ilike(f"%{kw}%")
                     )
                 )
            
            # Find matches
            matches = query.order_by(desc(Intervention.date_intervention)).limit(5).all()
            
            if matches:
                # Pick the most relevant? For now, pick the first (latest/most matching)
                intervention_id = matches[0].id
                logger.info(f"Resolved intervention by search: {intervention_id}")
            else:
                 return CopilotQueryResponse(
                     intent=CopilotIntentEnum.INTERVENTION_REPORT,
                     summary="Intervention not found.",
                     detailed_explanation=f"I couldn't find an intervention matching your criteria (Date: {search_params.get('date')}, Keywords: {search_params.get('keywords')}). Please provide an ID or valid date.",
                     confidence_level="low"
                 )

        intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
        if not intervention:
            raise HTTPException(status_code=404, detail="Intervention not found")

        # Gather details
        parts = []
        for p in intervention.parts:
            parts.append(f"{p.spare_part.designation} (qty: {p.quantite})")
            
        techs = []
        for t in intervention.technician_assignments:
            techs.append(f"{t.technician.prenom} {t.technician.nom} ({t.nombre_heures}h)")

        report_data = {
            "id": intervention.id,
            "equipment": intervention.equipment.designation,
            "date": intervention.date_intervention,
            "issue": f"{intervention.type_panne} - {intervention.categorie_panne}",
            "cause": intervention.cause,
            "resolution": intervention.resultat,
            "downtime": f"{intervention.duree_arret} hours",
            "total_cost": intervention.cout_total,
            "parts_used": parts,
            "technicians": techs
        }

        prompt = f"""
        You are a Maintenance Supervisor. Write a formal intervention report.

        Intervention Details:
        {json.dumps(report_data, default=str)}

        Instructions:
        1. Write a professional Summary.
        2. Create a Detailed Report section covering: Issue, Root Cause, Action Taken, Resources Used, and Costs.
        3. Recommend future prevention steps based on the cause.

        Response Format (JSON):
        STRICT JSON ONLY. No markdown formatted text, no preamble. Escape all quotes.
        {{
            "summary": "Formal summary...",
            "detailed_explanation": "Full report text...",
            "recommended_actions": [ ... ],
            "confidence_level": "high"
        }}
        """

        try:
            llm_response = await llm_service.generate_simple(prompt)
            data = self._parse_json_response(llm_response)
            
            supporting = [
                CopilotSupportingData(data_type="intervention", reference_id=str(intervention.id), description="Intervention Record", value=str(intervention.cout_total))
            ]

            return CopilotQueryResponse(
                intent=CopilotIntentEnum.INTERVENTION_REPORT,
                summary=data.get("summary", "Report generated."),
                detailed_explanation=data.get("detailed_explanation", llm_response),
                recommended_actions=self._sanitize_recommended_actions(data.get("recommended_actions", [])),
                supporting_data_references=supporting,
                confidence_level="high"
            )
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate report")

    async def _extract_intervention_search_params(self, message: str) -> Dict[str, Any]:
        """
        Uses LLM to extract date (YYYY-MM-DD) and keywords from query.
        """
        prompt = f"""
        Extract search parameters for a maintenance intervention from this query.
        Query: "{message}"
        
        Extract:
        1. Date: Convert any date mention (like "3/27/2025" or "yesterday") to YYYY-MM-DD format. If none, null.
        2. Keywords: Any meaningful words describing the failure (e.g. "mechanical", "pump", "leak"). Ignore stop words.
        
        Response JSON:
        {{
            "date": "YYYY-MM-DD" or null,
            "keywords": "string" or null
        }}
        """
        try:
            response = await llm_service.generate_simple(prompt)
            data = self._parse_json_response(response)
            return data
        except Exception as e:
            logger.error(f"Param extraction failed: {e}")
            return {}

    def _sanitize_recommended_actions(self, actions_raw: List[Dict[str, Any]]) -> List[CopilotRecommendedAction]:
        """
        Ensures recommended actions have all required fields.
        """
        sanitized = []
        for action in actions_raw:
            try:
                if not isinstance(action, dict):
                    continue
                    
                # Ensure 'priority' exists
                if "priority" not in action or action["priority"].lower() not in ["high", "medium", "low"]:
                    action["priority"] = "medium"
                
                # Ensure 'rationale' exists
                if "rationale" not in action:
                    action["rationale"] = "Recommended based on analysis."

                if "action" not in action:
                    continue # Skip invalid

                sanitized.append(CopilotRecommendedAction(**action))
            except Exception as e:
                logger.warning(f"Skipping invalid action chunk: {action} - {e}")
        
        return sanitized

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        Helper to parse JSON from LLM response.
        Handles markdown code blocks and attempts to extract JSON objects.
        """
        try:
            cleaned_text = text.strip()
            
            # 1. Strip markdown code blocks
            if "```" in cleaned_text:
                if "```json" in cleaned_text:
                    cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
                else:
                    cleaned_text = cleaned_text.split("```")[1].split("```")[0]
            
            # 2. Try to find the first '{' and last '}'
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                cleaned_text = cleaned_text[start_idx : end_idx + 1]
            
            # 3. Handle common LLM JSON syntax errors if needed (simple fix)
            # e.g., removal of trailing commas is complex, but let's assume valid JSON for now
            # after stripping wrapper text.
            
            return json.loads(cleaned_text)

        except Exception as e:
            logger.warning(f"Failed to parse JSON. Error: {e}. Raw Text: {text[:200]}...")
            # Fallback
            return {
                "summary": "Could not parse structured output.",
                "detailed_explanation": text,
                "recommended_actions": [],
                "confidence_level": "low"
            }

# Global instance
copilot_service = CopilotService()
