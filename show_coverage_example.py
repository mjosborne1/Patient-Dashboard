#!/usr/bin/env python3
"""
Test script to show complete Coverage resource with payor display
"""

import json
from bundler import create_request_bundle

def show_coverage_example():
    """Show a complete Coverage resource example"""
    
    print("Example Coverage resource with payor.display:")
    
    # Form data with Medicare billing
    form_data = {
        'patient_id': 'test-patient-123',
        'requester': 'Dr. Test',
        'organisation': 'Test Hospital',
        'urgency': 'routine',
        'reason': 'Test Request',
        'requestCategory': 'Pathology',
        'selectedTests': ['Full Blood Count'],
        'billingCategory': 'PUBLICPOL'  # Medicare
    }
    
    # Create bundle
    bundle = create_request_bundle(form_data)
    
    # Find and display the Coverage resource
    for entry in bundle.get('entry', []):
        if entry.get('resource', {}).get('resourceType') == 'Coverage':
            coverage = entry['resource']
            print(json.dumps(coverage, indent=2))
            break

if __name__ == "__main__":
    show_coverage_example()
