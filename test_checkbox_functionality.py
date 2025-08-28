#!/usr/bin/env python3
"""
Test script to verify checkbox functionality for specimen collection
"""

import json
from bundler import create_request_bundle

def test_checkbox_functionality():
    """Test that checkbox controls specimen creation"""
    
    print("Testing specimen checkbox functionality...")
    
    # Base form data for pathology request
    base_form_data = {
        'patient_id': 'test-patient-123',
        'requester': 'Dr. Test',
        'copy_to_practitioner': '',
        'copy_to_requester': '',
        'organisation': 'Test Hospital',
        'urgency': 'routine',
        'reason': 'Test Request',
        'requestCategory': 'Pathology',
        'selectedTests': ['Full Blood Count'],
        'specimenType': 'Blood',
        'specimenTypeCode': '',
        'collectionMethod': 'Venipuncture', 
        'collectionMethodCode': '',
        'bodySite': 'Arm',
        'bodySiteCode': '',
        'collectionDatetime': '2024-01-15T10:30:00'
    }
    
    print("\n1. Testing with checkbox UNCHECKED (specimenCollected=False):")
    form_data_unchecked = base_form_data.copy()
    # Don't include specimenCollected or set it to false
    bundle_unchecked = create_request_bundle(form_data_unchecked)
    
    # Check if specimen exists
    specimen_found = False
    for entry in bundle_unchecked.get('entry', []):
        if entry.get('resource', {}).get('resourceType') == 'Specimen':
            specimen_found = True
            break
    
    if specimen_found:
        print("✗ FAIL: Specimen resource found when checkbox is unchecked")
    else:
        print("✓ PASS: No specimen resource when checkbox is unchecked")
    
    print("\n2. Testing with checkbox CHECKED (specimenCollected=true):")
    form_data_checked = base_form_data.copy()
    form_data_checked['specimenCollected'] = 'true'
    bundle_checked = create_request_bundle(form_data_checked)
    
    # Check if specimen exists
    specimen_found = False
    specimen_resource = None
    for entry in bundle_checked.get('entry', []):
        if entry.get('resource', {}).get('resourceType') == 'Specimen':
            specimen_found = True
            specimen_resource = entry['resource']
            break
    
    if specimen_found:
        print("✓ PASS: Specimen resource found when checkbox is checked")
        if specimen_resource:
            print(f"   Specimen ID: {specimen_resource.get('id')}")
            print(f"   Specimen Type: {specimen_resource.get('type', {}).get('text', 'N/A')}")
    else:
        print("✗ FAIL: No specimen resource found when checkbox is checked")
    
    print("\n3. Testing ServiceRequest specimen references:")
    
    # Check ServiceRequest in unchecked scenario
    sr_unchecked = None
    for entry in bundle_unchecked.get('entry', []):
        if entry.get('resource', {}).get('resourceType') == 'ServiceRequest':
            sr_unchecked = entry['resource']
            break
    
    if sr_unchecked and 'specimen' in sr_unchecked:
        print("✗ FAIL: ServiceRequest has specimen reference when checkbox unchecked")
    else:
        print("✓ PASS: ServiceRequest has no specimen reference when checkbox unchecked")
    
    # Check ServiceRequest in checked scenario
    sr_checked = None
    for entry in bundle_checked.get('entry', []):
        if entry.get('resource', {}).get('resourceType') == 'ServiceRequest':
            sr_checked = entry['resource']
            break
    
    if sr_checked and 'specimen' in sr_checked:
        print("✓ PASS: ServiceRequest has specimen reference when checkbox checked")
        print(f"   Specimen Reference: {sr_checked['specimen']}")
    else:
        print("✗ FAIL: ServiceRequest missing specimen reference when checkbox checked")
    
    print("\nTest completed!")
    return bundle_unchecked, bundle_checked

if __name__ == "__main__":
    test_checkbox_functionality()
