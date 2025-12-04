#!/usr/bin/env python3
"""
Test script to verify Coverage.beneficiary references the patient correctly
"""

import json
from bundler import create_request_bundle

def test_coverage_beneficiary():
    """Test that Coverage.beneficiary references the patient correctly"""
    
    print("Testing Coverage.beneficiary reference to patient...")
    
    # Form data with billing category
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
    
    # Find the Coverage resource
    coverage = None
    for entry in bundle.get('entry', []):
        if entry.get('resource', {}).get('resourceType') == 'Coverage':
            coverage = entry['resource']
            break
    
    if coverage:
        beneficiary = coverage.get('beneficiary', {})
        patient_reference = beneficiary.get('reference', '')
        
        print(f"✓ Coverage resource found")
        print(f"✓ beneficiary.reference: '{patient_reference}'")
        
        # Verify the reference format
        expected_reference = f"Patient/{form_data['patient_id']}"
        if patient_reference == expected_reference:
            print(f"✓ PASS: beneficiary correctly references '{expected_reference}'")
        else:
            print(f"✗ FAIL: expected '{expected_reference}', got '{patient_reference}'")
            
        # Show complete Coverage structure
        print(f"\nComplete Coverage resource:")
        print(json.dumps(coverage, indent=2))
        
    else:
        print("✗ FAIL: No Coverage resource found in bundle")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_coverage_beneficiary()
