"""
Graph Query Service
Context enrichment using knowledge graph traversal
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set

from app.services.rag.graph.schema import NodeType, EdgeType, GraphNode
from app.services.rag.graph.graph_store import GMAOKnowledgeGraph, knowledge_graph

logger = logging.getLogger(__name__)


@dataclass
class GraphContext:
    """Context gathered from graph traversal"""
    
    # Related entities found
    related_entities: List[GraphNode] = field(default_factory=list)
    
    # Failure analysis results
    failure_chains: List[Dict[str, Any]] = field(default_factory=list)
    
    # Related documents
    related_documents: List[GraphNode] = field(default_factory=list)
    
    # Scope narrowing - document IDs to search
    scoped_document_ids: List[int] = field(default_factory=list)
    
    # Equipment context
    equipment_context: List[str] = field(default_factory=list)
    
    # Causal chains for root cause
    causal_chains: List[Dict[str, Any]] = field(default_factory=list)
    
    # Summary for LLM prompt
    summary: str = ""
    
    def add_entity(self, entity: GraphNode):
        if entity not in self.related_entities:
            self.related_entities.append(entity)
    
    def add_failure_chain(self, chain: Dict[str, Any]):
        self.failure_chains.append(chain)
    
    def add_document(self, doc: GraphNode):
        if doc not in self.related_documents:
            self.related_documents.append(doc)
            # Extract document ID
            if doc.source_id:
                try:
                    self.scoped_document_ids.append(int(doc.source_id))
                except ValueError:
                    pass
    
    def add_causal_chain(self, chain: Dict[str, Any]):
        self.causal_chains.append(chain)
    
    def build_summary(self) -> str:
        """Build a text summary for LLM context"""
        parts = []
        
        if self.equipment_context:
            parts.append(f"Related equipment: {', '.join(self.equipment_context)}")
        
        if self.failure_chains:
            fm_names = [fc.get('failure_mode', 'Unknown') for fc in self.failure_chains[:3]]
            parts.append(f"Known failure modes: {', '.join(fm_names)}")
        
        if self.causal_chains:
            causes = []
            for cc in self.causal_chains[:3]:
                if 'cause' in cc:
                    causes.append(cc['cause'])
            if causes:
                parts.append(f"Potential causes: {', '.join(causes)}")
        
        if self.related_documents:
            doc_names = [d.name for d in self.related_documents[:3]]
            parts.append(f"Relevant documents: {', '.join(doc_names)}")
        
        self.summary = " | ".join(parts) if parts else ""
        return self.summary
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_count": len(self.related_entities),
            "failure_chain_count": len(self.failure_chains),
            "document_count": len(self.related_documents),
            "scoped_document_ids": self.scoped_document_ids,
            "equipment_context": self.equipment_context,
            "causal_chain_count": len(self.causal_chains),
            "summary": self.summary or self.build_summary()
        }


class GraphQueryService:
    """
    Query service for context enrichment using knowledge graph.
    
    This service is used for:
    - Failure analysis and root cause reasoning
    - Finding related documents based on entities
    - Narrowing search scope using graph relationships
    
    NOT used for:
    - KPI calculations
    - Numeric aggregation
    - Direct answer generation
    """
    
    def __init__(self, graph: Optional[GMAOKnowledgeGraph] = None):
        self.graph = graph or knowledge_graph
    
    async def get_context_for_query(
        self,
        entities: List[str],
        query_intent: str
    ) -> GraphContext:
        """
        Get context enrichment for a query based on extracted entities.
        
        Args:
            entities: Entity names extracted from query
            query_intent: Type of context needed
                         "failure_analysis", "root_cause", "related_documents",
                         "equipment_info", "general"
                         
        Returns:
            GraphContext with enriched information
        """
        context = GraphContext()
        
        if not self.graph._initialized:
            logger.warning("Knowledge graph not initialized")
            return context
        
        for entity_name in entities:
            # Find node in graph
            node = self.graph.find_node_by_name(entity_name)
            if not node:
                continue
            
            context.add_entity(node)
            
            # Add to equipment context if it's equipment
            if node.type == NodeType.EQUIPMENT:
                context.equipment_context.append(node.name)
            
            # Get context based on intent
            if query_intent == "failure_analysis":
                await self._add_failure_context(node, context)
                
            elif query_intent == "root_cause":
                await self._add_causal_context(node, context)
                
            elif query_intent == "related_documents":
                await self._add_document_context(node, context)
                
            elif query_intent == "equipment_info":
                await self._add_equipment_context(node, context)
                
            else:  # general
                # Get immediate neighbors and documents
                await self._add_general_context(node, context)
        
        # Build summary
        context.build_summary()
        
        logger.debug(
            f"Graph context for {len(entities)} entities: "
            f"{len(context.related_entities)} related, "
            f"{len(context.related_documents)} docs"
        )
        
        return context
    
    async def _add_failure_context(
        self,
        node: GraphNode,
        context: GraphContext
    ):
        """Add failure analysis context for a node"""
        
        if node.type == NodeType.EQUIPMENT:
            # Get failure chains for equipment
            failure_chains = self.graph.find_failure_causes(node.id)
            for fc in failure_chains:
                context.add_failure_chain(fc)
            
            # Get related documents
            docs = self.graph.find_related_documents(node.id)
            for doc in docs:
                context.add_document(doc)
                
        elif node.type == NodeType.FAILURE_MODE:
            # Get effects and causes
            effects = self.graph.get_related_entities(
                node.id,
                edge_types=[EdgeType.HAS_EFFECT],
                max_hops=1
            )
            causes = self.graph.get_related_entities(
                node.id,
                edge_types=[EdgeType.CAUSED_BY],
                max_hops=1
            )
            
            context.add_failure_chain({
                "failure_mode": node.name,
                "failure_mode_id": node.id,
                "effects": [e.name for e in effects],
                "causes": [c.name for c in causes],
                "severity": node.properties.get("severity"),
                "rpn": node.properties.get("rpn")
            })
            
            # Get related documents
            docs = self.graph.find_related_documents(node.id)
            for doc in docs:
                context.add_document(doc)
    
    async def _add_causal_context(
        self,
        node: GraphNode,
        context: GraphContext
    ):
        """Add root cause context for a node"""
        
        # Trace back through CAUSES/CAUSED_BY edges
        causes = self.graph.get_related_entities(
            node.id,
            edge_types=[EdgeType.CAUSED_BY, EdgeType.CAUSES],
            max_hops=3,
            direction="both"
        )
        
        for cause in causes:
            context.add_entity(cause)
            context.add_causal_chain({
                "from": node.name,
                "cause": cause.name,
                "cause_type": cause.type.value
            })
        
        # Also get related failure modes if this is equipment
        if node.type == NodeType.EQUIPMENT:
            failure_chains = self.graph.find_failure_causes(node.id)
            for fc in failure_chains:
                context.add_failure_chain(fc)
    
    async def _add_document_context(
        self,
        node: GraphNode,
        context: GraphContext
    ):
        """Add related document context"""
        
        docs = self.graph.find_related_documents(node.id)
        for doc in docs:
            context.add_document(doc)
        
        # If no direct documents, try finding docs for related entities
        if not docs:
            related = self.graph.get_related_entities(node.id, max_hops=1)
            for rel_node in related[:5]:
                rel_docs = self.graph.find_related_documents(rel_node.id)
                for doc in rel_docs:
                    context.add_document(doc)
    
    async def _add_equipment_context(
        self,
        node: GraphNode,
        context: GraphContext
    ):
        """Add equipment-specific context"""
        
        if node.type == NodeType.EQUIPMENT:
            # Get components
            components = self.graph.get_related_entities(
                node.id,
                edge_types=[EdgeType.HAS_COMPONENT],
                max_hops=1
            )
            for comp in components:
                context.add_entity(comp)
            
            # Get recent interventions (limit to a few)
            interventions = self.graph.get_related_entities(
                node.id,
                edge_types=[EdgeType.FIXED_BY],
                max_hops=1
            )
            for inv in interventions[:5]:
                context.add_entity(inv)
            
            # Get failure modes
            failure_chains = self.graph.find_failure_causes(node.id)
            for fc in failure_chains:
                context.add_failure_chain(fc)
    
    async def _add_general_context(
        self,
        node: GraphNode,
        context: GraphContext
    ):
        """Add general context - neighbors and documents"""
        
        # Get immediate neighbors
        neighbors = self.graph.get_related_entities(node.id, max_hops=1)
        for neighbor in neighbors[:10]:
            context.add_entity(neighbor)
        
        # Get related documents
        docs = self.graph.find_related_documents(node.id)
        for doc in docs:
            context.add_document(doc)
    
    def get_scope_narrowing(
        self,
        entities: List[str]
    ) -> List[int]:
        """
        Get document IDs that should be prioritized in search
        based on entity relationships.
        
        Returns:
            List of document IDs to narrow search scope
        """
        document_ids: Set[int] = set()
        
        for entity_name in entities:
            node = self.graph.find_node_by_name(entity_name)
            if not node:
                continue
            
            # Get directly related documents
            docs = self.graph.find_related_documents(node.id)
            for doc in docs:
                if doc.source_id:
                    try:
                        document_ids.add(int(doc.source_id))
                    except ValueError:
                        pass
            
            # For equipment, also check related failure modes' documents
            if node.type == NodeType.EQUIPMENT:
                failure_modes = self.graph.get_related_entities(
                    node.id,
                    edge_types=[EdgeType.FAILS_WITH],
                    max_hops=1
                )
                for fm in failure_modes:
                    fm_docs = self.graph.find_related_documents(fm.id)
                    for doc in fm_docs:
                        if doc.source_id:
                            try:
                                document_ids.add(int(doc.source_id))
                            except ValueError:
                                pass
        
        return list(document_ids)


# Global instance
graph_query_service = GraphQueryService()
