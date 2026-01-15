"""
Query Router
Routes queries to appropriate handlers with confidence and graph awareness
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.services.rag.config import rag_settings
from app.services.rag.router.intent_classifier import (
    IntentClassifier, IntentType, ClassificationResult, intent_classifier
)
from app.services.rag.router.entity_extractor import (
    EntityExtractor, ExtractedEntities, entity_extractor
)
from app.services.rag.graph.graph_query import (
    GraphQueryService, GraphContext, graph_query_service
)

logger = logging.getLogger(__name__)


@dataclass
class RouteDecision:
    """Decision on how to route a query"""
    
    # What handlers to use (in order of priority)
    handlers: List[str]           # ["sql", "document", "graph", "hybrid"]
    primary_handler: str          # Main handler to use
    
    # Confidence and explanation
    confidence: float             # Overall confidence in decision
    reasoning: str                # Human-readable explanation
    
    # Classification details
    intent: IntentType
    intent_scores: Dict[str, float]
    
    # Extracted information
    kpi_type: Optional[str]       # For SQL handler
    entities: ExtractedEntities   # Extracted entities
    
    # Graph context for enrichment
    graph_context: Optional[GraphContext] = None
    scoped_document_ids: List[int] = field(default_factory=list)
    
    # Request tracking
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "handlers": self.handlers,
            "primary_handler": self.primary_handler,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "intent": self.intent.value,
            "intent_scores": self.intent_scores,
            "kpi_type": self.kpi_type,
            "entities": self.entities.to_dict() if self.entities else None,
            "graph_context": self.graph_context.to_dict() if self.graph_context else None,
            "scoped_document_ids": self.scoped_document_ids
        }


class QueryRouter:
    """
    Route queries with confidence and graph awareness.
    
    - Classifies intent (SQL, Document, Graph)
    - Falls back to HYBRID when confidence is low
    - Uses graph to narrow document scope
    - Provides explainable routing decisions
    """
    
    def __init__(
        self,
        classifier: Optional[IntentClassifier] = None,
        extractor: Optional[EntityExtractor] = None,
        graph_service: Optional[GraphQueryService] = None
    ):
        self.classifier = classifier or intent_classifier
        self.extractor = extractor or entity_extractor
        self.graph_service = graph_service or graph_query_service
    
    async def route(
        self,
        query: str,
        db: Optional[Session] = None
    ) -> RouteDecision:
        """
        Route a query to appropriate handlers.
        
        Args:
            query: User query text
            db: Database session for entity resolution
            
        Returns:
            RouteDecision with routing information
        """
        request_id = str(uuid.uuid4())[:8]
        reasoning_parts = []
        
        # 1. Classify intent
        classification = self.classifier.classify(query)
        reasoning_parts.append(
            f"Intent: {classification.intent.value} (conf={classification.confidence:.2f})"
        )
        
        # 2. Extract entities
        entities = await self.extractor.extract(query, db)
        if entities.equipment_names:
            reasoning_parts.append(f"Equipment: {', '.join(entities.equipment_names[:3])}")
        
        # 3. Determine handlers based on intent
        handlers = []
        primary = ""
        graph_context = None
        scoped_docs = []
        
        if classification.intent == IntentType.SQL_ANALYTICS:
            handlers = ["sql"]
            primary = "sql"
            reasoning_parts.append(f"KPI: {classification.kpi_detected or 'general'}")
            
        elif classification.intent == IntentType.DOCUMENT_RETRIEVAL:
            handlers = ["document"]
            primary = "document"
            
            # Use graph to narrow scope if entities found
            if entities.equipment_names and rag_settings.ENABLE_GRAPH_SCOPE:
                graph_context = await self.graph_service.get_context_for_query(
                    entities.equipment_names,
                    "related_documents"
                )
                scoped_docs = self.graph_service.get_scope_narrowing(
                    entities.equipment_names
                )
                if scoped_docs:
                    reasoning_parts.append(f"Graph scope: {len(scoped_docs)} docs")
                    
        elif classification.intent == IntentType.GRAPH_REASONING:
            handlers = ["graph", "document"]
            primary = "graph"
            
            # Get graph context for reasoning
            if entities.equipment_names:
                intent_type = self._get_graph_intent_type(query)
                graph_context = await self.graph_service.get_context_for_query(
                    entities.equipment_names,
                    intent_type
                )
                if graph_context.failure_chains:
                    reasoning_parts.append(
                        f"Graph: {len(graph_context.failure_chains)} failure chains"
                    )
                if graph_context.causal_chains:
                    reasoning_parts.append(
                        f"Causal: {len(graph_context.causal_chains)} paths"
                    )
                    
        else:  # HYBRID - low confidence
            handlers = ["sql", "document", "graph"]
            primary = "hybrid"
            reasoning_parts.append("Low confidence - using all paths")
            
            # Still get graph context for scope
            if entities.equipment_names:
                scoped_docs = self.graph_service.get_scope_narrowing(
                    entities.equipment_names
                )
        
        # Build final reasoning string
        reasoning = " | ".join(reasoning_parts)
        
        # Log decision
        self._log_decision(
            request_id=request_id,
            query=query,
            intent=classification.intent,
            confidence=classification.confidence,
            handlers=handlers,
            entities=entities
        )
        
        return RouteDecision(
            handlers=handlers,
            primary_handler=primary,
            confidence=classification.confidence,
            reasoning=reasoning,
            intent=classification.intent,
            intent_scores=classification.intent_scores,
            kpi_type=classification.kpi_detected,
            entities=entities,
            graph_context=graph_context,
            scoped_document_ids=scoped_docs,
            request_id=request_id
        )
    
    def _get_graph_intent_type(self, query: str) -> str:
        """Determine specific graph intent type"""
        query_lower = query.lower()
        
        if any(w in query_lower for w in ["why", "pourquoi", "cause", "root"]):
            return "root_cause"
        elif any(w in query_lower for w in ["fail", "panne", "défaillance"]):
            return "failure_analysis"
        elif any(w in query_lower for w in ["document", "manual", "procedure"]):
            return "related_documents"
        else:
            return "general"
    
    def _log_decision(
        self,
        request_id: str,
        query: str,
        intent: IntentType,
        confidence: float,
        handlers: List[str],
        entities: ExtractedEntities
    ):
        """Log routing decision for observability"""
        logger.info(
            "query_routed",
            extra={
                "request_id": request_id,
                "query_preview": query[:50].replace("\n", " "),
                "intent": intent.value,
                "confidence": round(confidence, 3),
                "handlers": handlers,
                "equipment_count": len(entities.equipment_ids),
                "has_date_range": entities.date_range is not None
            }
        )


# Global instance
query_router = QueryRouter()
