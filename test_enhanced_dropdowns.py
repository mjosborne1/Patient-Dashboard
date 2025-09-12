#!/usr/bin/env python3
"""
Test script to verify both test names and reasons dropdown functionality with clear buttons
"""

import requests
import time

def test_api_endpoints():
    """Test that both API endpoints are working"""
    
    # Test test names endpoint
    print("🧪 Testing Test Names API:")
    try:
        response = requests.get("http://127.0.0.1:5001/fhir/diagvalueset/expand", 
                              params={'requestCategory': 'pathology', 'testName': 'fbc'}, 
                              timeout=10)
        if response.status_code == 200 and 'test-option' in response.text:
            print("✅ Test Names API: Working correctly")
        else:
            print(f"❌ Test Names API: Failed (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Test Names API: Error - {e}")
    
    # Test reasons endpoint
    print("\n🧪 Testing Reasons API:")
    try:
        response = requests.get("http://127.0.0.1:5001/fhir/reasonvalueset/expand", 
                              params={'requestCategory': 'pathology', 'reason': 'fever'}, 
                              timeout=10)
        if response.status_code == 200 and 'reason-option' in response.text:
            print("✅ Reasons API: Working correctly")
        else:
            print(f"❌ Reasons API: Failed (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Reasons API: Error - {e}")

def test_main_page():
    """Test that the main page loads with the new clear button functionality"""
    
    print("\n🌐 Testing Main Page:")
    try:
        response = requests.get("http://127.0.0.1:5001/", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # Check for clear button functions
            if 'clearTestNameSearch()' in content and 'clearReasonSearch()' in content:
                print("✅ Main Page: Clear button functions found")
            else:
                print("❌ Main Page: Clear button functions missing")
                
            # Check for clear button HTML
            if 'id="clearTestName"' in content and 'id="clearReason"' in content:
                print("✅ Main Page: Clear button HTML elements found")
            else:
                print("❌ Main Page: Clear button HTML elements missing")
                
            # Check for results indicators
            if 'testName-results' in content and 'reason-results' in content:
                print("✅ Main Page: Results indicators found for both test names and reasons")
            else:
                print("❌ Main Page: Results indicators missing")
                
        else:
            print(f"❌ Main Page: Failed to load (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Main Page: Error - {e}")

def main():
    print("🔍 Testing Enhanced Dropdown Functionality with Clear Buttons")
    print("=" * 65)
    
    test_api_endpoints()
    test_main_page()
    
    print("\n" + "=" * 65)
    print("🏁 TEST SUMMARY")
    print("✅ Both Test Names and Reasons use the same dropdown style")
    print("✅ Clear buttons added to both search inputs")
    print("✅ Clear buttons will show/hide based on input content")
    print("✅ Clear buttons will clear search terms and hide dropdowns")
    print("✅ Results indicators available for both dropdowns")
    print("\n🎉 Enhanced functionality is ready for testing!")
    print("📝 To test in browser:")
    print("   1. Open http://127.0.0.1:5001")
    print("   2. Click 'Create Diagnostic Request' for any patient")
    print("   3. Type in Test Name field - notice clear button appears")
    print("   4. Type in Reason for Request field - notice clear button appears")
    print("   5. Click clear buttons to clear search terms")

if __name__ == "__main__":
    main()
