#!/usr/bin/env python3

"""
Test script to verify ValueSet expansion for pathology tests
"""

import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_valueset_expansion():
    """Test the terminology server ValueSet expansion"""
    
    print("Testing ValueSet expansion for pathology tests...")
    print("=" * 60)
    
    terminology_server = "https://r4.ontoserver.csiro.au/fhir"
    expand_url = f"{terminology_server}/ValueSet/$expand"
    valueset_url = "http://pathologyrequest.example.com.au/ValueSet/boosted"
    
    # Test searches
    test_queries = ["histology", "histo", "pathology", "blood"]
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        print("-" * 30)
        
        params = {
            "url": valueset_url,
            "filter": query,
            "count": 5  # Limit results for readability
        }
        
        try:
            print(f"Calling: {expand_url}")
            print(f"Parameters: {params}")
            
            resp = requests.get(expand_url, params=params, timeout=10)
            print(f"Response status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                contains = data.get("expansion", {}).get("contains", [])
                print(f"Found {len(contains)} results:")
                
                for i, item in enumerate(contains[:3]):  # Show first 3 results
                    code = item.get("code", "")
                    display = item.get("display", "")
                    system = item.get("system", "")
                    print(f"  {i+1}. Code: {code}")
                    print(f"     Display: {display}")
                    print(f"     System: {system}")
                    
                    # Check if this matches what we expect for histology
                    if "histol" in display.lower():
                        print(f"     ✅ Found histology match!")
                        
            else:
                print(f"❌ Request failed with status {resp.status_code}")
                print(f"Response: {resp.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_valueset_expansion()
