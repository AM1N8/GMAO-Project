"""
Graph Builder
Populates knowledge graph from database and documents
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.rag.graph.schema import (
    NodeType,
    EdgeType,
    GraphNode,
    GraphEdge
)
from app.services.rag.graph.graph_store import GMAOKnowledgeGraph, knowledge_graph

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Build knowledge graph from database and document metadata.
    
    Populates nodes from:
    - Equipment, Intervention, SparePart, Technician tables
    - FailureMode (AMDEC) table
    - RAGDocument table
    
    Populates edges from:
    - Table relationships (foreign keys)
    - Document metadata extraction (equipment mentions, etc.)
    """
    
    def __init__(self, graph: Optional[GMAOKnowledgeGraph] = None):
        self.graph = graph or knowledge_graph
    
    async def build_from_database(self, db: Session) -> Dict[str, int]:
        """
        Populate graph from database tables.
        
        Returns:
            Dict with counts of nodes/edges added
        """
        # Import models here to avoid circular imports
        from app.models import (
            Equipment, Intervention, SparePart, Technician,
            FailureMode, RAGDocument, DocumentStatus,
            InterventionPart, TechnicianAssignment, Skill
        )
        
        counts = {
            "equipment": 0,
            "interventions": 0,
            "spare_parts": 0,
            "technicians": 0,
            "failure_modes": 0,
            "documents": 0,
            "skills": 0,
            "edges": 0
        }
        
        logger.info("Building knowledge graph from database...")
        
        # 1. Add Equipment nodes
        equipment_list = db.query(Equipment).all()
        for eq in equipment_list:
            node = GraphNode(
                id=f"equipment:{eq.id}",
                type=NodeType.EQUIPMENT,
                name=eq.designation,
                properties={
                    "status": eq.status if hasattr(eq, 'status') else None,
                    "code": eq.code if hasattr(eq, 'code') else None,
                    "department": eq.department if hasattr(eq, 'department') else None
                },
                source_type="database",
                source_id=str(eq.id)
            )
            if self.graph.add_node(node):
                counts["equipment"] += 1
        
        # 2. Add SparePart nodes
        spare_parts = db.query(SparePart).all()
        for sp in spare_parts:
            node = GraphNode(
                id=f"spare_part:{sp.id}",
                type=NodeType.SPARE_PART,
                name=sp.designation,
                properties={
                    "reference": sp.reference if hasattr(sp, 'reference') else None,
                    "unit_cost": float(sp.unit_cost) if hasattr(sp, 'unit_cost') and sp.unit_cost else None,
                    "stock_quantity": sp.stock_quantity if hasattr(sp, 'stock_quantity') else None
                },
                source_type="database",
                source_id=str(sp.id)
            )
            if self.graph.add_node(node):
                counts["spare_parts"] += 1
        
        # 3. Add Technician nodes
        technicians = db.query(Technician).all()
        for tech in technicians:
            node = GraphNode(
                id=f"technician:{tech.id}",
                type=NodeType.TECHNICIAN,
                name=tech.name,
                properties={
                    "specialization": tech.specialization if hasattr(tech, 'specialization') else None,
                    "hourly_rate": float(tech.hourly_rate) if hasattr(tech, 'hourly_rate') and tech.hourly_rate else None
                },
                source_type="database",
                source_id=str(tech.id)
            )
            if self.graph.add_node(node):
                counts["technicians"] += 1
        
        # 4. Add Skill nodes (if they exist)
        try:
            skills = db.query(Skill).all()
            for skill in skills:
                node = GraphNode(
                    id=f"skill:{skill.id}",
                    type=NodeType.SKILL,
                    name=skill.name,
                    properties={
                        "category": skill.category if hasattr(skill, 'category') else None
                    },
                    source_type="database",
                    source_id=str(skill.id)
                )
                if self.graph.add_node(node):
                    counts["skills"] += 1
        except Exception:
            logger.debug("Skills table not available, skipping")
        
        # 5. Add Intervention nodes and edges
        interventions = db.query(Intervention).all()
        for inv in interventions:
            node = GraphNode(
                id=f"intervention:{inv.id}",
                type=NodeType.INTERVENTION,
                name=f"Intervention #{inv.id}",
                properties={
                    "type_panne": inv.type_panne if hasattr(inv, 'type_panne') else None,
                    "duree_arret": float(inv.duree_arret) if hasattr(inv, 'duree_arret') and inv.duree_arret else None,
                    "date": str(inv.date_intervention) if hasattr(inv, 'date_intervention') else None
                },
                source_type="database",
                source_id=str(inv.id)
            )
            if self.graph.add_node(node):
                counts["interventions"] += 1
            
            # Edge: Equipment -> fixed by -> Intervention
            if hasattr(inv, 'equipment_id') and inv.equipment_id:
                edge = GraphEdge(
                    source_id=f"equipment:{inv.equipment_id}",
                    target_id=f"intervention:{inv.id}",
                    type=EdgeType.FIXED_BY,
                    source="database:interventions"
                )
                if self.graph.add_edge(edge):
                    counts["edges"] += 1
        
        # 6. Add FailureMode nodes (AMDEC)
        try:
            failure_modes = db.query(FailureMode).all()
            for fm in failure_modes:
                node = GraphNode(
                    id=f"failure_mode:{fm.id}",
                    type=NodeType.FAILURE_MODE,
                    name=fm.mode_description if hasattr(fm, 'mode_description') else f"FM-{fm.id}",
                    properties={
                        "severity": fm.severity if hasattr(fm, 'severity') else None,
                        "occurrence": fm.occurrence if hasattr(fm, 'occurrence') else None,
                        "detection": fm.detection if hasattr(fm, 'detection') else None,
                        "rpn": fm.rpn if hasattr(fm, 'rpn') else None,
                        "component": fm.component if hasattr(fm, 'component') else None
                    },
                    source_type="database",
                    source_id=str(fm.id)
                )
                if self.graph.add_node(node):
                    counts["failure_modes"] += 1
                
                # Edge: Equipment -> fails with -> FailureMode
                if hasattr(fm, 'equipment_id') and fm.equipment_id:
                    edge = GraphEdge(
                        source_id=f"equipment:{fm.equipment_id}",
                        target_id=f"failure_mode:{fm.id}",
                        type=EdgeType.FAILS_WITH,
                        source="database:failure_modes"
                    )
                    if self.graph.add_edge(edge):
                        counts["edges"] += 1
                
                # Add Effect node if effect exists
                if hasattr(fm, 'effect') and fm.effect:
                    effect_node = GraphNode(
                        id=f"effect:{fm.id}",
                        type=NodeType.EFFECT,
                        name=fm.effect,
                        source_type="database",
                        source_id=str(fm.id)
                    )
                    self.graph.add_node(effect_node)
                    
                    edge = GraphEdge(
                        source_id=f"failure_mode:{fm.id}",
                        target_id=f"effect:{fm.id}",
                        type=EdgeType.HAS_EFFECT,
                        source="database:failure_modes"
                    )
                    if self.graph.add_edge(edge):
                        counts["edges"] += 1
                
                # Add Cause node if cause exists
                if hasattr(fm, 'cause') and fm.cause:
                    cause_node = GraphNode(
                        id=f"cause:{fm.id}",
                        type=NodeType.CAUSE,
                        name=fm.cause,
                        source_type="database",
                        source_id=str(fm.id)
                    )
                    self.graph.add_node(cause_node)
                    
                    edge = GraphEdge(
                        source_id=f"failure_mode:{fm.id}",
                        target_id=f"cause:{fm.id}",
                        type=EdgeType.CAUSED_BY,
                        source="database:failure_modes"
                    )
                    if self.graph.add_edge(edge):
                        counts["edges"] += 1
                        
        except Exception as e:
            logger.debug(f"FailureMode table not available: {e}")
        
        # 7. Add Document nodes
        try:
            documents = db.query(RAGDocument).filter(
                RAGDocument.status == DocumentStatus.INDEXED
            ).all()
            for doc in documents:
                node = GraphNode(
                    id=f"document:{doc.id}",
                    type=NodeType.DOCUMENT,
                    name=doc.filename,
                    properties={
                        "file_type": doc.file_type if hasattr(doc, 'file_type') else None
                    },
                    source_type="database",
                    source_id=str(doc.id)
                )
                if self.graph.add_node(node):
                    counts["documents"] += 1
        except Exception as e:
            logger.debug(f"RAGDocument table not available: {e}")
        
        # 8. Add relationship edges from association tables
        
        # Intervention -> uses -> SparePart
        try:
            intervention_parts = db.query(InterventionPart).all()
            for ip in intervention_parts:
                edge = GraphEdge(
                    source_id=f"intervention:{ip.intervention_id}",
                    target_id=f"spare_part:{ip.spare_part_id}",
                    type=EdgeType.USES_SPARE_PART,
                    properties={
                        "quantity": ip.quantity_used if hasattr(ip, 'quantity_used') else None
                    },
                    source="database:intervention_parts"
                )
                if self.graph.add_edge(edge):
                    counts["edges"] += 1
        except Exception as e:
            logger.debug(f"InterventionPart table not available: {e}")
        
        # Intervention -> performed by -> Technician
        try:
            assignments = db.query(TechnicianAssignment).all()
            for ta in assignments:
                edge = GraphEdge(
                    source_id=f"intervention:{ta.intervention_id}",
                    target_id=f"technician:{ta.technician_id}",
                    type=EdgeType.PERFORMED_BY,
                    properties={
                        "hours_worked": float(ta.hours_worked) if hasattr(ta, 'hours_worked') and ta.hours_worked else None
                    },
                    source="database:technician_assignments"
                )
                if self.graph.add_edge(edge):
                    counts["edges"] += 1
        except Exception as e:
            logger.debug(f"TechnicianAssignment table not available: {e}")
        
        # Save the graph
        self.graph.save()
        
        logger.info(
            f"Built knowledge graph: {sum(counts.values()) - counts['edges']} nodes, "
            f"{counts['edges']} edges"
        )
        
        return counts
    
    async def add_document_relationships(
        self,
        document_id: int,
        extracted_metadata: Dict[str, Any],
        db: Session
    ) -> int:
        """
        Add relationships from document metadata extraction.
        
        Called after document processing to link documents
        to mentioned entities.
        
        Args:
            document_id: The document database ID
            extracted_metadata: Metadata extracted from document
            db: Database session
            
        Returns:
            Number of edges added
        """
        from app.models import Equipment, FailureMode
        
        doc_node_id = f"document:{document_id}"
        edges_added = 0
        
        # Ensure document node exists
        if doc_node_id not in self.graph.graph:
            logger.warning(f"Document node {doc_node_id} not in graph")
            return 0
        
        # Link to mentioned equipment
        for eq_name in extracted_metadata.get("equipment_mentions", []):
            eq = db.query(Equipment).filter(
                Equipment.designation.ilike(f"%{eq_name}%")
            ).first()
            
            if eq:
                edge = GraphEdge(
                    source_id=f"equipment:{eq.id}",
                    target_id=doc_node_id,
                    type=EdgeType.DESCRIBED_IN,
                    confidence=0.8,
                    source="document:extraction"
                )
                if self.graph.add_edge(edge):
                    edges_added += 1
        
        # Link to mentioned failure modes
        for fm_desc in extracted_metadata.get("failure_modes", []):
            try:
                fm = db.query(FailureMode).filter(
                    FailureMode.mode_description.ilike(f"%{fm_desc}%")
                ).first()
                
                if fm:
                    edge = GraphEdge(
                        source_id=f"failure_mode:{fm.id}",
                        target_id=doc_node_id,
                        type=EdgeType.DESCRIBED_IN,
                        confidence=0.7,
                        source="document:extraction"
                    )
                    if self.graph.add_edge(edge):
                        edges_added += 1
            except Exception:
                pass
        
        if edges_added > 0:
            self.graph.save()
            logger.info(f"Added {edges_added} document relationships for doc {document_id}")
        
        return edges_added


# Global builder instance
graph_builder = GraphBuilder()
