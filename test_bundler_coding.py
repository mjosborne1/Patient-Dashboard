#!/usr/bin/env python3

"""
Test script to verify that ServiceRequest codes are properly generated with coding arrays
"""

import sys
import os
import json
import logging

# Add current directory to path to import bundler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bundler import _build_servicerequest_code

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_servicerequest_code_generation():
    """Test the _build_servicerequest_code function with different inputs"""
    
    print("Testing ServiceRequest code generation...")
    print("=" * 50)
    
    # Test case 1: Test with both code and display (should include coding array)
    test1 = {
        "code": "252416005",
        "display": "Histology"
    }
    
    print(f"\nTest 1 - Full coding with code and display:")
    print(f"Input: {test1}")
    result1 = _build_servicerequest_code(test1)
    print(f"Output: {json.dumps(result1, indent=2)}")
    
    # Verify it has coding array
    has_coding = "coding" in result1
    print(f"✅ Has coding array: {has_coding}")
    
    # Test case 2: Test with empty code (should only have text)
    test2 = {
        "code": "",
        "display": "Custom Test Name"
    }
    
    print(f"\nTest 2 - Text-only (no code):")
    print(f"Input: {test2}")
    result2 = _build_servicerequest_code(test2)
    print(f"Output: {json.dumps(result2, indent=2)}")
    
    # Verify it doesn't have coding array
    has_coding = "coding" in result2
    print(f"✅ No coding array: {not has_coding}")
    
    # Test case 3: Test with None code (should only have text)
    test3 = {
        "display": "Another Custom Test"
    }
    
    print(f"\nTest 3 - Missing code field:")
    print(f"Input: {test3}")
    result3 = _build_servicerequest_code(test3)
    print(f"Output: {json.dumps(result3, indent=2)}")
    
    # Verify it doesn't have coding array
    has_coding = "coding" in result3
    print(f"✅ No coding array: {not has_coding}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_servicerequest_code_generation()
