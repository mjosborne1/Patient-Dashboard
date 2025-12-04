#!/usr/bin/env python3

import requests
import json

def test_dropdown_data():
    """Test what data is returned for histology search"""
    
    # Test the actual FHIR endpoint
    terminology_server = "https://r4.ontoserver.csiro.au/fhir"
    expand_url = f"{terminology_server}/ValueSet/$expand"
    valueset_url = 'http://pathologyrequest.example.com.au/ValueSet/boosted'
    
    params = {
        "url": valueset_url,
        "filter": "histology",
        "count": 15
    }
    
    print("Testing FHIR terminology server...")
    print(f"URL: {expand_url}")
    print(f"Params: {params}")
    print("-" * 50)
    
    try:
        resp = requests.get(expand_url, params=params, timeout=10)
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            contains = data.get("expansion", {}).get("contains", [])
            print(f"Found {len(contains)} results:")
            
            for i, item in enumerate(contains):
                code = item.get("code", "")
                display = item.get("display", "")
                print(f"{i+1}. Code: '{code}' | Display: '{display}'")
                
            print("\n" + "="*50)
            print("Testing local Flask app endpoint...")
            
            # Test the local Flask endpoint
            local_url = "http://127.0.0.1:5001/fhir/diagvalueset/expand"
            local_params = {
                "requestCategory": "pathology",
                "testName": "histology"
            }
            
            local_resp = requests.get(local_url, params=local_params, timeout=10)
            print(f"Local Status Code: {local_resp.status_code}")
            print(f"Local Response Length: {len(local_resp.text)}")
            print("Local Response Content:")
            print(local_resp.text)
            
        else:
            print(f"Error: {resp.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_dropdown_data()
