#!/usr/bin/env python3
"""
Test script to verify that FHIR server URL settings are working correctly
"""

import requests
import json

def test_server_url_header():
    """Test that the X-FHIR-Server-URL header is being processed correctly"""
    
    base_url = "http://127.0.0.1:5001"
    
    # Test 1: Request without custom header (should use default)
    print("Test 1: Request without custom header (should use default aucore.aidbox.beda.software)")
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"  Default server: {data.get('fhir_server', 'NOT FOUND')}")
    else:
        print(f"  Error: {response.status_code}")
    
    # Test 2: Request with custom header
    print("\nTest 2: Request with custom header")
    custom_server = "https://smile.sparked-fhir.com/aucore/fhir/DEFAULT"
    headers = {"X-FHIR-Server-URL": custom_server}
    response = requests.get(f"{base_url}/health", headers=headers)
    if response.status_code == 200:
        data = response.json()
        returned_server = data.get('fhir_server', 'NOT FOUND')
        print(f"  Custom server sent: {custom_server}")
        print(f"  Server returned: {returned_server}")
        if returned_server == custom_server:
            print("  ✓ Custom server URL is working correctly!")
        else:
            print("  ✗ Custom server URL is NOT working")
    else:
        print(f"  Error: {response.status_code}")
    
    # Test 3: Test another custom server
    print("\nTest 3: Test another custom server")
    another_server = "https://test.example.com/fhir"
    headers = {"X-FHIR-Server-URL": another_server}
    response = requests.get(f"{base_url}/health", headers=headers)
    if response.status_code == 200:
        data = response.json()
        returned_server = data.get('fhir_server', 'NOT FOUND')
        print(f"  Custom server sent: {another_server}")
        print(f"  Server returned: {returned_server}")
        if returned_server == another_server:
            print("  ✓ Second custom server URL is working correctly!")
        else:
            print("  ✗ Second custom server URL is NOT working")
    else:
        print(f"  Error: {response.status_code}")

if __name__ == "__main__":
    print("Testing FHIR server URL header functionality...")
    print("=" * 50)
    
    try:
        test_server_url_header()
        print("\n" + "=" * 50)
        print("✓ Server URL header tests completed!")
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to Flask app. Make sure it's running on http://127.0.0.1:5001")
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
