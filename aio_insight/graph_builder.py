import json
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ObjectTypeNode:
    def __init__(self, data: Dict[str, Any]):
        self.original_data = data  # Keep original data
        self.id = data.get('id')  # Original ID from the data
        self.name = data.get('name', 'Unknown')
        self.type = data.get('type', 0)
        self.description = data.get('description', '')
        self.icon = data.get('icon', {})
        self.position = data.get('position', 0)
        self.parent_id = data.get('parentObjectTypeId')
        self.attributes = data.get('attributes', [])
        self.children = []

    def __repr__(self):
        return f"ObjectTypeNode(name={self.name}, id={self.id}, parent_id={self.parent_id})"


class SchemaBuilder:
    def __init__(self, object_types: List[Dict[str, Any]]):
        self.object_types = object_types
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.children: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.root_nodes: List[Dict[str, Any]] = []
        self.name_to_node: Dict[str, Dict[str, Any]] = {}  # New mapping from names to nodes
        self.initialize_nodes()

    def initialize_nodes(self):
        """Create nodes and track their relationships."""
        # First create all nodes and store by ID and name
        for obj_data in self.object_types:
            node_id = str(obj_data.get('id'))
            node_name = obj_data.get('name', 'Unknown')
            if node_id:
                node = {
                    'id': obj_data.get('id'),
                    'name': node_name,
                    'type': obj_data.get('type', 0),
                    'description': obj_data.get('description', ''),
                    'icon': obj_data.get('icon', {}),
                    'position': obj_data.get('position', 0),
                    'parent_id': obj_data.get('parentObjectTypeId'),
                    'attributes': obj_data.get('attributes', [])
                }
                self.nodes[node_id] = node
                self.name_to_node[node_name] = node
                logger.debug(f"Added node: {node_name} (ID: {node_id})")

        # Build parent-child relationships using names
        for node_id, node in self.nodes.items():
            parent_id = str(node['parent_id']) if node['parent_id'] is not None else None
            if parent_id is None or parent_id not in self.nodes:
                self.root_nodes.append(node)
                node['parent_name'] = None
                logger.debug(f"Root node: {node['name']}")
            else:
                parent_node = self.nodes[parent_id]
                parent_name = parent_node['name']
                node['parent_name'] = parent_name  # Store parent name instead of ID
                self.children[parent_name].append(node)
                logger.debug(f"Child node: {node['name']} -> Parent: {parent_name}")

        # Sort root nodes by position
        self.root_nodes.sort(key=lambda x: x['position'])
        logger.info(f"Initialized {len(self.nodes)} nodes, {len(self.root_nodes)} root nodes")

    def get_creation_order(self) -> List[Dict[str, Any]]:
        """Get nodes in proper creation order (parents before children)."""
        ordered = []
        processed = set()

        def process_node(node: Dict[str, Any]):
            node_name = node['name']
            if node_name in processed:
                return

            # Process parent first if exists
            parent_name = node.get('parent_name')
            if parent_name and parent_name in self.name_to_node:
                process_node(self.name_to_node[parent_name])

            # Add this node
            processed.add(node_name)
            ordered.append(node)
            logger.debug(f"Adding to order: {node_name}")

            # Process children sorted by position
            children = sorted(self.children[node_name], key=lambda x: x['position'])
            for child in children:
                process_node(child)

        # Start with root nodes
        for root in self.root_nodes:
            process_node(root)

        # Add any remaining nodes that might have broken parent references
        for node in self.nodes.values():
            if node['name'] not in processed:
                process_node(node)

        print(f"Creation order: {[node['name'] for node in ordered]}")
        return ordered

def create_schema_structure(object_types: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create schema structure for implementation."""
    logger.info(f"Creating schema structure from {len(object_types)} object types")
    builder = SchemaBuilder(object_types)
    ordered = builder.get_creation_order()
    logger.info(f"Created ordered structure with {len(ordered)} nodes")
    return ordered

