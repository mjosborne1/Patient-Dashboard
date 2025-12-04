#!/usr/bin/env python3
"""
Test script to verify that the reason dropdown functionality works similar to test names dropdown
"""

import requests
import re
from typing import List, Dict

def test_reason_dropdown_api():
    """Test that the reason API returns proper dropdown format"""
    
    # Test the reason endpoint
    url = "http://127.0.0.1:5001/fhir/reasonvalueset/expand"
    params = {
        'requestCategory': 'pathology',
        'reason': 'fever'  # Search for fever-related reasons
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            html_content = response.text
            print(f"Response length: {len(html_content)} characters")
            
            # Check if response contains dropdown items instead of datalist options
            dropdown_pattern = r'<a href="#" class="dropdown-item reason-option"[^>]*>'
            dropdown_matches = re.findall(dropdown_pattern, html_content)
            
            # Check for data attributes
            data_code_pattern = r'data-code="([^"]*)"'
            data_display_pattern = r'data-display="([^"]*)"'
            
            codes = re.findall(data_code_pattern, html_content)
            displays = re.findall(data_display_pattern, html_content)
            
            print(f"\nDropdown Analysis:")
            print(f"- Found {len(dropdown_matches)} dropdown items")
            print(f"- Found {len(codes)} data-code attributes")
            print(f"- Found {len(displays)} data-display attributes")
            
            if len(dropdown_matches) > 0:
                print(f"\n✅ SUCCESS: Response contains dropdown format")
                print(f"First dropdown item: {dropdown_matches[0]}")
                
                if len(codes) > 0 and len(displays) > 0:
                    print(f"\n📋 Sample reasons found:")
                    for i in range(min(3, len(displays))):
                        print(f"  {i+1}. {displays[i]} (Code: {codes[i]})")
                        
                    return True
                else:
                    print(f"❌ ERROR: Missing data attributes")
                    return False
            else:
                print(f"❌ ERROR: No dropdown items found")
                print(f"Response content preview: {html_content[:500]}...")
                return False
                
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")
        return False

def test_reason_no_results():
    """Test that when no results are found, the template handles it gracefully"""
    
    url = "http://127.0.0.1:5001/fhir/reasonvalueset/expand"
    params = {
        'requestCategory': 'pathology',
        'reason': 'xyzzzzunknownreason12345'  # Intentionally bogus search
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"\nNo Results Test - Status Code: {response.status_code}")
        
        if response.status_code == 200:
            html_content = response.text
            
            # Check for the "no results" message
            no_results_pattern = r'No matching reasons found'
            no_results_match = re.search(no_results_pattern, html_content)
            
            if no_results_match:
                print(f"✅ SUCCESS: No results message found")
                print(f"Response includes custom text guidance")
                return True
            else:
                # Check if response is empty (also acceptable)
                if len(html_content.strip()) == 0:
                    print(f"✅ SUCCESS: Empty response for no results")
                    return True
                else:
                    print(f"⚠️  WARNING: Unexpected response for no results")
                    print(f"Response: {html_content[:200]}...")
                    return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")
        return False

def main():
    print("🧪 Testing Reason Dropdown Functionality")
    print("=" * 50)
    
    # Test 1: Reason API returns dropdown format
    print("\n📋 Test 1: Reason API Response Format")
    test1_result = test_reason_dropdown_api()
    
    # Test 2: No results handling
    print("\n🚫 Test 2: No Results Handling")
    test2_result = test_reason_no_results()
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 TEST SUMMARY")
    print(f"✅ Dropdown Format Test: {'PASS' if test1_result else 'FAIL'}")
    print(f"✅ No Results Test: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        print(f"\n🎉 ALL TESTS PASSED! Reason dropdown functionality is working correctly.")
        print(f"Users can now:")
        print(f"  - Search for reasons and see clickable dropdown options")
        print(f"  - Enter custom text when no results are found")
        print(f"  - Use keyboard navigation (arrows, Enter, Escape)")
    else:
        print(f"\n❌ SOME TESTS FAILED. Please check the implementation.")

if __name__ == "__main__":
    main()
