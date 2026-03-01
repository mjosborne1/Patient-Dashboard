"""
Test script to validate the Mermaid diagram generation integration.

This script tests:
1. Creating a sample FHIR bundle
2. Parsing resources from the bundle
3. Building a graph from the resources
4. Generating Mermaid diagram syntax
"""

import json
from fhir_parser import extract_resources
from graph_builder import build_graph, get_graph_stats
from mermaid_generator import generate_mermaid


def test_mermaid_integration():
    """Test the complete mermaid diagram generation pipeline."""
    
    # Load a sample bundle (use the service_request_bundle.json)
    with open('./json/service_request_bundle.json', 'r', encoding='utf-8') as f:
        bundle = json.load(f)
    
    print("✓ Loaded sample bundle")
    
    # Extract resources
    resources = extract_resources(bundle)
    print(f"✓ Extracted {len(resources)} resources from bundle")
    
    # Build graph
    graph = build_graph(resources)
    stats = get_graph_stats(graph)
    print(f"✓ Built graph with {stats['nodes']} nodes, {stats['edges']} edges, {stats['external_refs']} external references")
    
    # Print some node details
    print("\nNodes in graph:")
    for node_id, label in list(graph.nodes.items())[:5]:
        print(f"  - {label[:50]}...")
    
    # Generate mermaid diagram
    mermaid_text = generate_mermaid(graph, "Test Bundle Diagram")
    print(f"\n✓ Generated Mermaid diagram ({len(mermaid_text)} characters)")
    
    # Print first few lines of the diagram
    print("\nFirst few lines of Mermaid diagram:")
    for line in mermaid_text.split('\n')[:10]:
        print(f"  {line}")
    
    # Validate mermaid syntax
    assert mermaid_text.startswith('flowchart'), "Mermaid diagram should start with 'flowchart'"
    assert '-->' in mermaid_text, "Mermaid diagram should contain edges (-->)"
    
    print("\n✅ All tests passed!")
    print("\nYou can now:")
    print("1. Start the Flask app: python app.py")
    print("2. Navigate to a patient details page")
    print("3. Create a diagnostic request bundle")
    print("4. Click 'Draw Mermaid' button to visualize the bundle")
    
    return True


if __name__ == '__main__':
    try:
        test_mermaid_integration()
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
