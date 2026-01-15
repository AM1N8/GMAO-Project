"""
Knowledge Graph Schema
Node and edge type definitions for GMAO knowledge graph
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


class NodeType(Enum):
    """Types of nodes in the knowledge graph"""
    EQUIPMENT = "equipment"
    COMPONENT = "component"
    FAILURE_MODE = "failure_mode"
    EFFECT = "effect"
    CAUSE = "cause"
    INTERVENTION = "intervention"
    SPARE_PART = "spare_part"
    DOCUMENT = "document"
    DOCUMENT_SECTION = "document_section"
    TECHNICIAN = "technician"
    SKILL = "skill"


class EdgeType(Enum):
    """Types of edges (relationships) in the knowledge graph"""
    # Equipment relationships
    HAS_COMPONENT = "has_component"
    PART_OF = "part_of"
    
    # Failure relationships
    FAILS_WITH = "fails_with"
    CAUSES = "causes"
    CAUSED_BY = "caused_by"
    HAS_EFFECT = "has_effect"
    
    # Maintenance relationships
    FIXED_BY = "fixed_by"
    USES_SPARE_PART = "uses_spare_part"
    REPLACED_WITH = "replaced_with"
    
    # Documentation relationships
    DESCRIBED_IN = "described_in"
    REFERENCES = "references"
    CONTAINS_SECTION = "contains_section"
    
    # Personnel relationships
    PERFORMED_BY = "performed_by"
    REQUIRES_SKILL = "requires_skill"
    HAS_SKILL = "has_skill"
    
    # AMDEC/FMEA specific
    MITIGATED_BY = "mitigated_by"
    DETECTED_BY = "detected_by"


@dataclass
class GraphNode:
    """A node in the knowledge graph"""
    id: str
    type: NodeType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Optional source tracking
    source_type: Optional[str] = None  # "database", "document", "extracted"
    source_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "properties": self.properties,
            "source_type": self.source_type,
            "source_id": self.source_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphNode":
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            name=data["name"],
            properties=data.get("properties", {}),
            source_type=data.get("source_type"),
            source_id=data.get("source_id")
        )


@dataclass
class GraphEdge:
    """An edge (relationship) in the knowledge graph"""
    source_id: str
    target_id: str
    type: EdgeType
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Confidence and provenance
    confidence: float = 1.0  # 0.0 to 1.0
    source: Optional[str] = None  # Where this relationship was found
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.value,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEdge":
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            type=EdgeType(data["type"]),
            properties=data.get("properties", {}),
            confidence=data.get("confidence", 1.0),
            source=data.get("source")
        )


# Predefined edge relationship rules
# Defines which node types can be connected by which edge types
VALID_EDGE_RULES = {
    EdgeType.HAS_COMPONENT: (NodeType.EQUIPMENT, NodeType.COMPONENT),
    EdgeType.PART_OF: (NodeType.COMPONENT, NodeType.EQUIPMENT),
    EdgeType.FAILS_WITH: (NodeType.COMPONENT, NodeType.FAILURE_MODE),
    EdgeType.CAUSES: (NodeType.CAUSE, NodeType.FAILURE_MODE),
    EdgeType.CAUSED_BY: (NodeType.FAILURE_MODE, NodeType.CAUSE),
    EdgeType.HAS_EFFECT: (NodeType.FAILURE_MODE, NodeType.EFFECT),
    EdgeType.FIXED_BY: (NodeType.FAILURE_MODE, NodeType.INTERVENTION),
    EdgeType.USES_SPARE_PART: (NodeType.INTERVENTION, NodeType.SPARE_PART),
    EdgeType.DESCRIBED_IN: (None, NodeType.DOCUMENT),  # Any node can be described in doc
    EdgeType.PERFORMED_BY: (NodeType.INTERVENTION, NodeType.TECHNICIAN),
    EdgeType.REQUIRES_SKILL: (NodeType.COMPONENT, NodeType.SKILL),
    EdgeType.HAS_SKILL: (NodeType.TECHNICIAN, NodeType.SKILL),
}
