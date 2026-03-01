"""
Mermaid Diagram Generator Module

Converts FHIR resource graphs to Mermaid flowchart syntax.
Adapted from fhir-bundle-viz for use in Patient Dashboard.
"""

import re
from typing import Dict, Set
from graph_builder import Graph


def generate_mermaid(graph: Graph, bundle_title: str = "FHIR Bundle Diagram") -> str:
    """
    Generate Mermaid flowchart syntax from a graph.
    
    Args:
        graph: Graph object with nodes and edges
        bundle_title: Title for the diagram
        
    Returns:
        Mermaid diagram as a string
    """
    lines = []
    
    # Start with flowchart declaration (left-right layout)
    lines.append("flowchart LR")
    
    # Add title as a comment
    lines.append(f"    %% {bundle_title}")
    lines.append("")
    
    # Create sanitized node IDs mapping
    node_id_map = _create_node_id_map(set(graph.nodes.keys()))
    
    # Separate external and internal nodes
    external_nodes = [(node_id, label) for node_id, label in graph.nodes.items() 
                      if node_id in graph.external_refs]
    internal_nodes = [(node_id, label) for node_id, label in graph.nodes.items() 
                      if node_id not in graph.external_refs]
    
    # Add internal nodes
    for node_id, label in internal_nodes:
        sanitized_id = node_id_map[node_id]
        escaped_label = _escape_mermaid_label(label)
        lines.append(f"    {sanitized_id}[\"{escaped_label}\"]")
    
    # Add external reference nodes with rounded stadium shape
    if external_nodes:
        lines.append("")
        lines.append("    %% External References")
        for node_id, label in external_nodes:
            sanitized_id = node_id_map[node_id]
            escaped_label = _escape_mermaid_label(label)
            # Use stadium shape (rounded ends) for external references
            lines.append(f"    {sanitized_id}([\"{escaped_label}\"])")
    
    lines.append("")
    
    # Add edges with labels
    for source_id, target_id, edge_label in graph.edges:
        source_sanitized = node_id_map.get(source_id)
        target_sanitized = node_id_map.get(target_id)
        
        if source_sanitized and target_sanitized:
            escaped_edge_label = _escape_mermaid_label(edge_label)
            lines.append(f"    {source_sanitized} -->|{escaped_edge_label}| {target_sanitized}")
    
    # Add styling for external reference nodes
    if external_nodes:
        lines.append("")
        lines.append("    %% Styling for external references")
        lines.append("    classDef externalRef fill:#f0f0f0,stroke:#999,stroke-width:2px,stroke-dasharray: 5 5")
        external_node_ids = [node_id_map[node_id] for node_id, _ in external_nodes]
        lines.append(f"    class {','.join(external_node_ids)} externalRef")

    # Add styling for Task group nodes
    if graph.group_tasks:
        lines.append("")
        lines.append("    %% Styling for group tasks")
        lines.append("    classDef taskGroup fill:#ffe9a8,stroke:#b07a00,stroke-width:2px")
        group_node_ids = [node_id_map[node_id] for node_id in graph.group_tasks if node_id in node_id_map]
        if group_node_ids:
            lines.append(f"    class {','.join(group_node_ids)} taskGroup")
    
    return '\n'.join(lines)


def _create_node_id_map(node_ids: Set[str]) -> Dict[str, str]:
    """
    Create a mapping from original node IDs to Mermaid-safe IDs.
    
    Mermaid node IDs should:
    - Start with a letter
    - Contain only alphanumeric characters and underscores
    - Be unique
    
    Args:
        node_ids: Set of original node IDs (UUIDs)
        
    Returns:
        Dictionary mapping original IDs to sanitized IDs
    """
    id_map = {}
    counter = {}
    
    for node_id in node_ids:
        # Create a base ID by taking alphanumeric chars from UUID or external ID
        # Remove hyphens and ensure it starts with a letter
        base = re.sub(r'[^a-zA-Z0-9]', '', node_id)
        
        # Ensure it starts with a letter
        if base and not base[0].isalpha():
            base = 'n' + base
        elif not base:
            base = 'node'
        
        # Truncate to reasonable length
        base = base[:20]
        
        # Make it unique by adding counter if needed
        if base not in counter:
            counter[base] = 0
            sanitized = base
        else:
            counter[base] += 1
            sanitized = f"{base}_{counter[base]}"
        
        id_map[node_id] = sanitized
    
    return id_map


def _escape_mermaid_label(label: str) -> str:
    """
    Escape special characters in Mermaid labels.
    
    Mermaid labels in quotes need to escape:
    - Double quotes as #quot;
    - Newlines
    
    Args:
        label: Original label text
        
    Returns:
        Escaped label safe for Mermaid
    """
    if not label:
        return ""
    
    # Replace double quotes with #quot; (Mermaid HTML entity)
    label = label.replace('"', '#quot;')
    
    # Replace other potentially problematic characters
    label = label.replace('\n', ' ')
    label = label.replace('\r', '')
    
    # Limit label length to avoid overly wide diagrams
    max_length = 100
    if len(label) > max_length:
        label = label[:max_length-3] + '...'
    
    return label
