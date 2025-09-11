#!/usr/bin/env python3
"""
Test script to verify SNOMED code lookup functionality in bundler.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bundler import lookup_snomed_code

def test_snomed_lookup():
    """Test the SNOMED code lookup function"""
    
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
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_snomed_lookup()
