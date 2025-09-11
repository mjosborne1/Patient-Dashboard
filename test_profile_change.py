#!/usr/bin/env python3
"""
Test script to verify the specimen profile change from AU Core to AU Base
"""

def test_profile_reference():
    """Test that the specimen profile reference has been updated correctly"""
    
    # Read the bundler.py file
    with open('bundler.py', 'r') as f:
        content = f.read()
    
    # Check for the correct AU Base Specimen profile
    au_base_profile = "http://hl7.org.au/fhir/StructureDefinition/au-specimen"
    au_core_profile = "http://hl7.org.au/fhir/core/StructureDefinition/au-core-specimen"
    
    if au_base_profile in content:
        print("✓ AU Base Specimen profile found in bundler.py")
        profile_correct = True
    else:
        print("✗ AU Base Specimen profile NOT found in bundler.py")
        profile_correct = False
    
    if au_core_profile in content:
        print("✗ AU Core Specimen profile still found in bundler.py (should be removed)")
        profile_correct = False
    else:
        print("✓ AU Core Specimen profile correctly removed from bundler.py")
    
    return profile_correct

def test_selected_tests_placement():
    """Test that the selected tests display is placed correctly in the HTML"""
    
    # Read the HTML file
    with open('templates/diag_request.html', 'r') as f:
        content = f.read()
    
    # Find the testName input section
    testname_section = content.find('id="testName"')
    if testname_section == -1:
        print("✗ Could not find testName input in HTML")
        return False
    
    # Find the selected tests display section after testName
    selected_tests_section = content.find('id="selectedTestsDisplay"', testname_section)
    if selected_tests_section == -1:
        print("✗ Could not find selectedTestsDisplay after testName")
        return False
    
    # Find the specimen section
    specimen_section = content.find('id="specimenSection"')
    if specimen_section == -1:
        print("✗ Could not find specimenSection")
        return False
    
    # Check that selectedTestsDisplay comes before specimenSection
    if selected_tests_section < specimen_section:
        print("✓ selectedTestsDisplay correctly placed before specimen section")
        return True
    else:
        print("✗ selectedTestsDisplay incorrectly placed after specimen section")
        return False

if __name__ == "__main__":
    print("Testing specimen profile change and HTML layout...")
    print()
    
    profile_test = test_profile_reference()
    print()
    
    layout_test = test_selected_tests_placement()
    print()
    
    if profile_test and layout_test:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
