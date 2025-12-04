#!/usr/bin/env python3

"""
Test script to simulate the full diagnostic request processing
"""

import sys
import os
import json
import logging

# Add current directory to path to import bundler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bundler import create_request_bundle

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

def test_diagnostic_request_processing():
    """Test the full diagnostic request processing"""
    
    print("Testing diagnostic request processing...")
    print("=" * 60)
    
    # Simulate form data with proper test structure (like what should come from frontend)
    test_form_data = {
        'patient_id': 'test-patient-123',
        'requestCategory': 'Pathology',
        'selectedTests': json.dumps([
            {
                "code": "252416005",
                "display": "Histology",
                "display_sequence": 1
            },
            {
                "code": "",  # Test with empty code
                "display": "Custom Test Name",
                "display_sequence": 2
            }
        ]),
        'selectedReasons': json.dumps([]),
        'requester': 'test-practitioner',
        'priority': 'routine'
    }
    
    print("Form data being processed:")
    for key, value in test_form_data.items():
        if key == 'selectedTests':
            # Pretty print the parsed JSON
            parsed_tests = json.loads(value)
            print(f"  {key}: {json.dumps(parsed_tests, indent=4)}")
        else:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Processing bundle...")
    
    try:
        # Process the form data through the bundler
        bundle = create_request_bundle(
            form_data=test_form_data,
            fhir_server_url="https://test.example.com/fhir",
            auth_credentials=None
        )
        
        print("Bundle created successfully!")
        
        # Extract and examine ServiceRequest entries
        service_requests = [entry for entry in bundle.get('entry', []) 
                          if entry.get('resource', {}).get('resourceType') == 'ServiceRequest']
        
        print(f"\nFound {len(service_requests)} ServiceRequest(s):")
        
        for i, sr_entry in enumerate(service_requests):
            sr = sr_entry['resource']
            code = sr.get('code', {})
            print(f"\nServiceRequest #{i+1}:")
            print(f"  Code structure: {json.dumps(code, indent=2)}")
            
            # Check if it has coding array
            if 'coding' in code:
                print(f"  ✅ Has coding array with system: {code['coding'][0].get('system')}")
                print(f"  ✅ SNOMED code: {code['coding'][0].get('code')}")
                print(f"  ✅ Display: {code['coding'][0].get('display')}")
            else:
                print(f"  ⚠️  Only has text field: {code.get('text')}")
                
    except Exception as e:
        print(f"❌ Error processing bundle: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_diagnostic_request_processing()
