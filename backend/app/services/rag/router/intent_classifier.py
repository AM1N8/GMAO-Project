"""
Intent Classifier
Classifies queries with confidence scoring
"""

import logging
import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

from app.services.rag.config import rag_settings

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of query intents"""
    SQL_ANALYTICS = "sql_analytics"      # KPIs, metrics, counts - use KPIService
    DOCUMENT_RETRIEVAL = "document"      # Procedures, manuals - use hierarchical search
    GRAPH_REASONING = "graph"            # Why? Root cause? Related? - use GraphRAG
    HYBRID = "hybrid"                    # Needs multiple paths or low confidence


@dataclass
class ClassificationResult:
    """Result of intent classification"""
    intent: IntentType
    confidence: float           # 0.0 - 1.0
    kpi_detected: Optional[str] # mtbf, mttr, availability, cost, etc.
    entities: List[str]         # Extracted equipment, components
    reasoning_keywords: bool    # Contains "why", "cause", "related"
    intent_scores: Dict[str, float]  # All intent scores for explainability


class IntentClassifier:
    """
    Classify queries with confidence scoring.
    
    Falls back to HYBRID when confidence is below threshold.
    """
    
    # KPI patterns with associated intent
    KPI_PATTERNS = {
        "mtbf": {
            "keywords": ["mtbf", "mean time between failure", "temps moyen entre pannes", 
                        "fiabilité", "reliability", "failure rate"],
            "kpi_type": "mtbf",
            "weight": 0.4
        },
        "mttr": {
            "keywords": ["mttr", "mean time to repair", "temps moyen de réparation",
                        "repair time", "durée intervention", "durée de réparation"],
            "kpi_type": "mttr",
            "weight": 0.4
        },
        "availability": {
            "keywords": ["availability", "disponibilité", "uptime", "taux de disponibilité",
                        "operational time", "temps de fonctionnement"],
            "kpi_type": "availability",
            "weight": 0.4
        },
        "cost": {
            "keywords": ["cost", "coût", "dépense", "budget", "maintenance cost",
                        "coût de maintenance", "expense", "spending"],
            "kpi_type": "cost",
            "weight": 0.35
        },
        "count": {
            "keywords": ["how many", "combien", "count", "nombre", "total",
                        "number of", "quantity"],
            "kpi_type": "count",
            "weight": 0.3
        },
        "trend": {
            "keywords": ["trend", "tendance", "over time", "evolution", "historique",
                        "last month", "this year", "since"],
            "kpi_type": "trend",
            "weight": 0.25
        }
    }
    
    # Document retrieval patterns
    DOCUMENT_PATTERNS = {
        "procedure": {
            "keywords": ["how to", "comment", "procedure", "procédure", "sop",
                        "steps", "étapes", "instructions", "guide"],
            "weight": 0.4
        },
        "manual": {
            "keywords": ["manual", "manuel", "documentation", "spec", "specification",
                        "technical document"],
            "weight": 0.35
        },
        "action": {
            "keywords": ["replace", "remplacer", "install", "installer", "repair",
                        "réparer", "configure", "configurer", "maintain"],
            "weight": 0.3
        }
    }
    
    # Graph reasoning patterns
    GRAPH_PATTERNS = {
        "root_cause": {
            "keywords": ["why", "pourquoi", "root cause", "cause racine", "reason",
                        "raison", "because", "parce que"],
            "weight": 0.4
        },
        "failure": {
            "keywords": ["failure mode", "mode de défaillance", "fail", "défaillance",
                        "breakdown", "panne", "malfunction"],
            "weight": 0.35
        },
        "relationship": {
            "keywords": ["related", "lié", "connected", "associé", "impact",
                        "affect", "consequence", "effect", "effet"],
            "weight": 0.3
        },
        "amdec": {
            "keywords": ["amdec", "fmea", "fmeca", "rpn", "severity", "sévérité",
                        "occurrence", "detection", "détection"],
            "weight": 0.35
        }
    }
    
    def __init__(self, confidence_threshold: Optional[float] = None):
        self.confidence_threshold = (
            confidence_threshold or 
            rag_settings.INTENT_CONFIDENCE_THRESHOLD
        )
    
    def classify(self, query: str) -> ClassificationResult:
        """
        Classify query intent with confidence scoring.
        
        Args:
            query: User query text
            
        Returns:
            ClassificationResult with intent, confidence, and metadata
        """
        query_lower = query.lower()
        
        # Calculate scores for each intent type
        sql_score, kpi_detected = self._score_sql_intent(query_lower)
        doc_score = self._score_document_intent(query_lower)
        graph_score = self._score_graph_intent(query_lower)
        
        # Check for reasoning keywords
        reasoning_keywords = self._has_reasoning_keywords(query_lower)
        
        # Collect all scores
        intent_scores = {
            IntentType.SQL_ANALYTICS.value: sql_score,
            IntentType.DOCUMENT_RETRIEVAL.value: doc_score,
            IntentType.GRAPH_REASONING.value: graph_score
        }
        
        # Determine primary intent
        max_score = max(intent_scores.values())
        
        if max_score >= self.confidence_threshold:
            # Clear winner
            if sql_score == max_score:
                intent = IntentType.SQL_ANALYTICS
                confidence = sql_score
            elif doc_score == max_score:
                intent = IntentType.DOCUMENT_RETRIEVAL
                confidence = doc_score
            else:
                intent = IntentType.GRAPH_REASONING
                confidence = graph_score
        else:
            # Low confidence - use HYBRID
            intent = IntentType.HYBRID
            confidence = 1.0 - max_score  # Confidence in needing hybrid
        
        # Apply boost for reasoning keywords
        if reasoning_keywords and intent != IntentType.HYBRID:
            # Boost graph reasoning if reasoning keywords present
            if intent != IntentType.GRAPH_REASONING:
                # Consider switching to hybrid or graph
                if graph_score > 0.5:
                    intent = IntentType.GRAPH_REASONING
                    confidence = graph_score
        
        result = ClassificationResult(
            intent=intent,
            confidence=round(confidence, 3),
            kpi_detected=kpi_detected,
            entities=[],  # Will be populated by EntityExtractor
            reasoning_keywords=reasoning_keywords,
            intent_scores=intent_scores
        )
        
        logger.debug(
            f"Intent classification: {intent.value} (conf={confidence:.2f}), "
            f"scores={intent_scores}"
        )
        
        return result
    
    def _score_sql_intent(self, query: str) -> Tuple[float, Optional[str]]:
        """Score likelihood of SQL/KPI intent"""
        score = 0.0
        kpi_detected = None
        
        for pattern_name, pattern_config in self.KPI_PATTERNS.items():
            for keyword in pattern_config["keywords"]:
                if keyword in query:
                    weight = pattern_config["weight"]
                    score += weight
                    
                    if kpi_detected is None:
                        kpi_detected = pattern_config["kpi_type"]
                    break
        
        # Additional signals
        # Numeric/comparative questions
        if any(w in query for w in ["average", "moyenne", "sum", "total", 
                                     "maximum", "minimum", "percentage"]):
            score += 0.2
        
        # Time-based analytics
        if any(w in query for w in ["last month", "this year", "depuis", 
                                     "between", "during", "period"]):
            score += 0.15
        
        # Comparative
        if any(w in query for w in ["compare", "vs", "versus", "difference"]):
            score += 0.1
        
        return min(score, 1.0), kpi_detected
    
    def _score_document_intent(self, query: str) -> float:
        """Score likelihood of document retrieval intent"""
        score = 0.0
        
        for pattern_name, pattern_config in self.DOCUMENT_PATTERNS.items():
            for keyword in pattern_config["keywords"]:
                if keyword in query:
                    score += pattern_config["weight"]
                    break
        
        # Question words suggesting procedural info
        if query.startswith(("how", "comment", "what is the procedure")):
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_graph_intent(self, query: str) -> float:
        """Score likelihood of graph/reasoning intent"""
        score = 0.0
        
        for pattern_name, pattern_config in self.GRAPH_PATTERNS.items():
            for keyword in pattern_config["keywords"]:
                if keyword in query:
                    score += pattern_config["weight"]
                    break
        
        # Additional reasoning signals
        if self._has_reasoning_keywords(query):
            score += 0.2
        
        return min(score, 1.0)
    
    def _has_reasoning_keywords(self, query: str) -> bool:
        """Check for causal reasoning keywords"""
        reasoning_words = [
            "why", "pourquoi", "cause", "reason", "raison",
            "because", "parce que", "due to", "result of",
            "leads to", "consequence"
        ]
        return any(word in query for word in reasoning_words)


# Global instance
intent_classifier = IntentClassifier()
