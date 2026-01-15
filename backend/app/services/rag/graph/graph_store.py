"""
GMAO Knowledge Graph Store
NetworkX-based graph storage for relationship reasoning
"""

import logging
import pickle
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
from collections import defaultdict

import networkx as nx

from app.services.rag.config import rag_settings
from app.services.rag.graph.schema import (
    NodeType,
    EdgeType,
    GraphNode,
    GraphEdge
)

logger = logging.getLogger(__name__)


class GMAOKnowledgeGraph:
    """
    Knowledge graph for GMAO domain using NetworkX.
    
    Used for relationship reasoning and context enrichment.
    NOT used for KPI calculations or numeric aggregation.
    """
    
    def __init__(self, store_path: Optional[str] = None):
        self.store_path = Path(store_path or rag_settings.GRAPH_STORE_PATH)
        self.graph = nx.DiGraph()
        self._node_by_name: Dict[str, str] = {}  # name -> node_id lookup
        self._nodes_by_type: Dict[NodeType, Set[str]] = defaultdict(set)
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the knowledge graph"""
        try:
            self.store_path.mkdir(parents=True, exist_ok=True)
            
            graph_file = self.store_path / "gmao_graph.pkl"
            if graph_file.exists():
                self.load(str(graph_file))
                logger.info(
                    f"Loaded knowledge graph: {self.graph.number_of_nodes()} nodes, "
                    f"{self.graph.number_of_edges()} edges"
                )
            else:
                logger.info("Created new empty knowledge graph")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize knowledge graph: {e}")
            return False
    
    def add_node(self, node: GraphNode) -> bool:
        """Add a node to the graph"""
        try:
            self.graph.add_node(
                node.id,
                type=node.type.value,
                name=node.name,
                source_type=node.source_type,
                source_id=node.source_id,
                **node.properties
            )
            
            # Update lookups
            self._node_by_name[node.name.lower()] = node.id
            self._nodes_by_type[node.type].add(node.id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to add node {node.id}: {e}")
            return False
    
    def add_edge(self, edge: GraphEdge) -> bool:
        """Add an edge (relationship) to the graph"""
        try:
            # Verify nodes exist
            if edge.source_id not in self.graph:
                logger.warning(f"Source node {edge.source_id} not found")
                return False
            if edge.target_id not in self.graph:
                logger.warning(f"Target node {edge.target_id} not found")
                return False
            
            self.graph.add_edge(
                edge.source_id,
                edge.target_id,
                type=edge.type.value,
                confidence=edge.confidence,
                source=edge.source,
                **edge.properties
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to add edge: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID"""
        if node_id not in self.graph:
            return None
        
        data = self.graph.nodes[node_id]
        return GraphNode(
            id=node_id,
            type=NodeType(data["type"]),
            name=data["name"],
            properties={k: v for k, v in data.items() 
                       if k not in ["type", "name", "source_type", "source_id"]},
            source_type=data.get("source_type"),
            source_id=data.get("source_id")
        )
    
    def find_node_by_name(
        self,
        name: str,
        node_type: Optional[NodeType] = None
    ) -> Optional[GraphNode]:
        """Find a node by name (case-insensitive)"""
        name_lower = name.lower()
        
        node_id = self._node_by_name.get(name_lower)
        if node_id:
            node = self.get_node(node_id)
            if node and (node_type is None or node.type == node_type):
                return node
        
        # Partial match fallback
        for stored_name, node_id in self._node_by_name.items():
            if name_lower in stored_name or stored_name in name_lower:
                node = self.get_node(node_id)
                if node and (node_type is None or node.type == node_type):
                    return node
        
        return None
    
    def get_related_entities(
        self,
        node_id: str,
        edge_types: Optional[List[EdgeType]] = None,
        max_hops: int = 2,
        direction: str = "both"  # "out", "in", "both"
    ) -> List[GraphNode]:
        """
        Get entities related to a node within N hops.
        
        Args:
            node_id: Starting node ID
            edge_types: Filter by edge types (None = all)
            max_hops: Maximum traversal depth
            direction: Edge direction to follow
            
        Returns:
            List of related nodes
        """
        if node_id not in self.graph:
            return []
        
        edge_type_values = [e.value for e in edge_types] if edge_types else None
        
        visited = set()
        related = []
        queue = [(node_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_hops:
                continue
            
            visited.add(current_id)
            
            # Get neighbors based on direction
            neighbors = []
            if direction in ["out", "both"]:
                neighbors.extend(self.graph.successors(current_id))
            if direction in ["in", "both"]:
                neighbors.extend(self.graph.predecessors(current_id))
            
            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue
                
                # Check edge type filter
                if edge_type_values:
                    edge_data = self.graph.edges.get((current_id, neighbor_id), {})
                    if not edge_data:
                        edge_data = self.graph.edges.get((neighbor_id, current_id), {})
                    
                    if edge_data.get("type") not in edge_type_values:
                        continue
                
                node = self.get_node(neighbor_id)
                if node:
                    related.append(node)
                    queue.append((neighbor_id, depth + 1))
        
        return related
    
    def find_failure_causes(
        self,
        equipment_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find failure modes and their causes for equipment.
        
        This is a key query for AMDEC/FMEA reasoning.
        
        Returns:
            List of failure cause chains
        """
        if equipment_id not in self.graph:
            return []
        
        failure_paths = []
        
        # Find components of this equipment
        components = self.get_related_entities(
            equipment_id,
            edge_types=[EdgeType.HAS_COMPONENT],
            max_hops=1,
            direction="out"
        )
        
        for component in components:
            # Find failure modes of this component
            failure_modes = self.get_related_entities(
                component.id,
                edge_types=[EdgeType.FAILS_WITH],
                max_hops=1,
                direction="out"
            )
            
            for fm in failure_modes:
                # Find effects
                effects = self.get_related_entities(
                    fm.id,
                    edge_types=[EdgeType.HAS_EFFECT],
                    max_hops=1,
                    direction="out"
                )
                
                # Find causes
                causes = self.get_related_entities(
                    fm.id,
                    edge_types=[EdgeType.CAUSED_BY],
                    max_hops=1,
                    direction="out"
                )
                
                # Find interventions that fix this
                interventions = self.get_related_entities(
                    fm.id,
                    edge_types=[EdgeType.FIXED_BY],
                    max_hops=1,
                    direction="out"
                )
                
                failure_paths.append({
                    "equipment_id": equipment_id,
                    "component": component.name,
                    "component_id": component.id,
                    "failure_mode": fm.name,
                    "failure_mode_id": fm.id,
                    "severity": fm.properties.get("severity"),
                    "occurrence": fm.properties.get("occurrence"),
                    "detection": fm.properties.get("detection"),
                    "rpn": fm.properties.get("rpn"),
                    "effects": [e.name for e in effects],
                    "causes": [c.name for c in causes],
                    "interventions": [i.name for i in interventions]
                })
        
        return failure_paths
    
    def find_related_documents(
        self,
        entity_id: str
    ) -> List[GraphNode]:
        """Find documents that describe an entity"""
        return self.get_related_entities(
            entity_id,
            edge_types=[EdgeType.DESCRIBED_IN],
            max_hops=1,
            direction="out"
        )
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[GraphNode]:
        """Get all nodes of a specific type"""
        node_ids = self._nodes_by_type.get(node_type, set())
        return [self.get_node(nid) for nid in node_ids if self.get_node(nid)]
    
    def save(self, path: Optional[str] = None) -> bool:
        """Save graph to disk"""
        try:
            save_path = Path(path) if path else self.store_path / "gmao_graph.pkl"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "graph": self.graph,
                "node_by_name": self._node_by_name,
                "nodes_by_type": {k.value: list(v) for k, v in self._nodes_by_type.items()}
            }
            
            with open(save_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"Saved knowledge graph to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")
            return False
    
    def load(self, path: str) -> bool:
        """Load graph from disk"""
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            
            self.graph = data["graph"]
            self._node_by_name = data.get("node_by_name", {})
            
            # Reconstruct nodes_by_type
            nodes_by_type_raw = data.get("nodes_by_type", {})
            self._nodes_by_type = defaultdict(set)
            for type_str, node_ids in nodes_by_type_raw.items():
                self._nodes_by_type[NodeType(type_str)] = set(node_ids)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load graph: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        type_counts = {
            node_type.value: len(node_ids)
            for node_type, node_ids in self._nodes_by_type.items()
        }
        
        return {
            "initialized": self._initialized,
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": type_counts,
            "is_connected": nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else False
        }
    
    def clear(self):
        """Clear the graph"""
        self.graph.clear()
        self._node_by_name.clear()
        self._nodes_by_type.clear()


# Global instance
knowledge_graph = GMAOKnowledgeGraph()
