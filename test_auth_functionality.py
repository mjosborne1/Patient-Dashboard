#!/usr/bin/env python3
"""
Test script to verify that FHIR authentication is working correctly
"""

import requests
import json

def test_fhir_auth():
    """Test that FHIR authentication headers are being processed correctly"""
    
    base_url = "http://127.0.0.1:5001"
    
    print("Test 1: Request without authentication headers")
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"  Server: {data.get('fhir_server', 'NOT FOUND')}")
        print("  ✓ No auth request successful")
    else:
        print(f"  Error: {response.status_code}")
    
    print("\nTest 2: Request with authentication headers")
    headers = {
        "X-FHIR-Server-URL": "https://test.example.com/fhir",
        "X-FHIR-Username": "testuser",
        "X-FHIR-Password": "testpass"
    }
    response = requests.get(f"{base_url}/health", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"  Custom server: {data.get('fhir_server', 'NOT FOUND')}")
        print("  ✓ Auth headers sent successfully")
    else:
        print(f"  Error: {response.status_code}")
    
    print("\nTest 3: Make a request that triggers FHIR calls (this will show auth in logs)")
    headers = {
        "X-FHIR-Server-URL": "https://aucore.aidbox.beda.software/fhir",
        "X-FHIR-Username": "testuser", 
        "X-FHIR-Password": "testpass"
    }
    
    # This should trigger a fhir_get call and we should see auth in the logs
    response = requests.get(f"{base_url}/fhir/Patients", headers=headers)
    print(f"  Patient request status: {response.status_code}")
    if response.status_code == 200:
        print("  ✓ Request with auth completed - check Flask logs for auth usage")
    else:
        print("  ✗ Request failed - but check Flask logs to see if auth was attempted")

if __name__ == "__main__":
    print("Testing FHIR authentication functionality...")
    print("=" * 60)
    
    try:
        test_fhir_auth()
        print("\n" + "=" * 60)
        print("✓ Authentication header tests completed!")
        print("Check the Flask app logs to see if 'using auth testuser:*****' appears")
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to Flask app. Make sure it's running on http://127.0.0.1:5001")
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
