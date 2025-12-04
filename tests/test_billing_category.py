#!/usr/bin/env python3
"""
Test script to verify billing category payor display functionality
"""

import json
from bundler import create_request_bundle

def test_billing_category_payor():
    """Test that billing category sets Coverage.payor.display correctly"""
    
    print("Testing billing category payor display functionality...")
    
    # Base form data
    base_form_data = {
        'patient_id': 'test-patient-123',
        'requester': 'Dr. Test',
        'organisation': 'Test Hospital',
        'urgency': 'routine',
        'reason': 'Test Request',
        'requestCategory': 'Pathology',
        'selectedTests': ['Full Blood Count']
    }
    
    # Test different billing categories
    billing_categories = [
        ('PUBLICPOL', 'Medicare'),
        ('VET', 'Department of Veterans\' Affairs'),
        ('pay', 'Private Pay'),
        ('payconc', 'Private Pay with Concession'),
        ('AUPUBHOSP', 'Public Hospital'),
        ('WCBPOL', 'Workers\' Compensation')
    ]
    
    for code, expected_display in billing_categories:
        print(f"\n{code}: Testing billing category '{code}' -> '{expected_display}'")
        
        # Create form data with this billing category
        form_data = base_form_data.copy()
        form_data['billingCategory'] = code
        
        # Create bundle
        bundle = create_request_bundle(form_data)
        
        # Find the Coverage resource
        coverage = None
        for entry in bundle.get('entry', []):
            if entry.get('resource', {}).get('resourceType') == 'Coverage':
                coverage = entry['resource']
                break
        
        if coverage:
            # Check if payor exists and has correct display
            payor = coverage.get('payor', [])
            if payor and len(payor) > 0:
                payor_display = payor[0].get('display', '')
                if payor_display == expected_display:
                    print(f"   ✓ PASS: payor.display = '{payor_display}'")
                else:
                    print(f"   ✗ FAIL: payor.display = '{payor_display}', expected '{expected_display}'")
            else:
                print(f"   ✗ FAIL: payor field missing or empty")
            
            # Also check type.text for consistency
            type_text = coverage.get('type', {}).get('text', '')
            if type_text == expected_display:
                print(f"   ✓ PASS: type.text = '{type_text}'")
            else:
                print(f"   ✗ FAIL: type.text = '{type_text}', expected '{expected_display}'")
                
        else:
            print(f"   ✗ FAIL: No Coverage resource found in bundle")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_billing_category_payor()
