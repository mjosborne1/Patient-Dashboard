#!/usr/bin/env python3
"""
Test script to create a sample bundle with specimen and verify SNOMED codes are included
"""

import json
from datetime import datetime
from bundler import create_request_bundle, lookup_snomed_code

def test_snomed_lookup():
    """Test the SNOMED lookup function directly"""
    print("Testing SNOMED code lookup functionality...")
    
    # Test specimen type lookup
    print("\n1. Testing specimen type lookup:")
    specimen_type_code = lookup_snomed_code("blood", "http://hl7.org.au/fhir/ValueSet/specimen-type-1")
    print(f"   Blood specimen type: {specimen_type_code}")
    
    # Test collection method lookup
    print("\n2. Testing collection method lookup:")
    collection_method_code = lookup_snomed_code("venipuncture", "http://hl7.org.au/fhir/ValueSet/specimen-collection-procedure-1")
    print(f"   Venipuncture collection method: {collection_method_code}")
    
    # Test body site lookup
    print("\n3. Testing body site lookup:")
    body_site_code = lookup_snomed_code("arm", "http://hl7.org.au/fhir/ValueSet/body-site-1")
    print(f"   Arm body site: {body_site_code}")
    
    return specimen_type_code, collection_method_code, body_site_code

def test_bundle_creation():
    """Test bundle creation with specimen including SNOMED code lookup"""
    
    print("\nTesting bundle creation with specimen and SNOMED code lookup...")
    
    # Test data simulating form submission with empty codes to trigger lookup
    form_data = {
        'patient_id': 'test-patient-123',
        'requester': 'Dr. Test',
        'copy_to_practitioner': '',
        'copy_to_requester': '',
        'organisation': 'Test Hospital',
        'urgency': 'routine',
        'reason': 'Test Request',
        'requestCategory': 'Pathology',
        'test_names': ['Full Blood Count'],
        'specimenType': 'Blood',
        'specimenTypeCode': '',  # Empty to trigger lookup
        'collectionMethod': 'Venipuncture', 
        'collectionMethodCode': '',  # Empty to trigger lookup
        'bodySite': 'Arm',
        'bodySiteCode': '',  # Empty to trigger lookup
        'collectionDatetime': '2024-01-15T10:30:00'
    }
    
    print(f"\nInput form data: {json.dumps(form_data, indent=2)}")
    
    # Create bundle
    bundle = create_request_bundle(form_data)
    
    # Find the specimen resource in the bundle
    specimen = None
    for entry in bundle.get('entry', []):
        if entry.get('resource', {}).get('resourceType') == 'Specimen':
            specimen = entry['resource']
            break
    
    if specimen:
        print(f"\nFound specimen resource:")
        print(json.dumps(specimen, indent=2))
        
        # Verify SNOMED codes are present
        print("\nVerifying SNOMED codes...")
        
        # Check specimen type coding
        if 'type' in specimen and 'coding' in specimen['type']:
            type_coding = specimen['type']['coding'][0] if specimen['type']['coding'] else {}
            print(f"✓ Specimen type code: {type_coding.get('code', 'MISSING')}")
            print(f"  Display: {type_coding.get('display', 'MISSING')}")
        else:
            print("✗ Specimen type coding missing")
        
        # Check collection method coding
        if ('collection' in specimen and 
            'method' in specimen['collection'] and 
            'coding' in specimen['collection']['method']):
            method_coding = specimen['collection']['method']['coding'][0] if specimen['collection']['method']['coding'] else {}
            print(f"✓ Collection method code: {method_coding.get('code', 'MISSING')}")
            print(f"  Display: {method_coding.get('display', 'MISSING')}")
        else:
            print("✗ Collection method coding missing")
        
        # Check body site coding
        if ('collection' in specimen and 
            'bodySite' in specimen['collection'] and 
            'coding' in specimen['collection']['bodySite']):
            bodysite_coding = specimen['collection']['bodySite']['coding'][0] if specimen['collection']['bodySite']['coding'] else {}
            print(f"✓ Body site code: {bodysite_coding.get('code', 'MISSING')}")
            print(f"  Display: {bodysite_coding.get('display', 'MISSING')}")
        else:
            print("✗ Body site coding missing")
    else:
        print("✗ No specimen resource found in bundle")
    
    print("\nTest completed!")
    return bundle

if __name__ == "__main__":
    # First test SNOMED lookup directly
    test_snomed_lookup()
    
    # Then test bundle creation with specimens
    test_bundle_creation()
