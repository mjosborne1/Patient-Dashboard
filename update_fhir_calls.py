#!/usr/bin/env python3
"""
Script to update all fhir_get calls in app.py to include auth_credentials parameter
"""

import re

def update_fhir_get_calls(file_path):
    """Update all fhir_get calls to include auth_credentials parameter"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match fhir_get calls that already have fhir_server_url but not auth_credentials
    pattern = r'fhir_get\((.*?fhir_server_url=get_fhir_server_url\(\))(.*?)\)'
    
    def replacement(match):
        full_match = match.group(0)
        before_server_url = match.group(1)
        after_server_url = match.group(2)
        
        # Check if auth_credentials is already present
        if 'auth_credentials=' in full_match:
            return full_match  # Already has auth_credentials, don't modify
        
        # Insert auth_credentials parameter after fhir_server_url
        return f'fhir_get({before_server_url}, auth_credentials=get_fhir_auth_credentials(){after_server_url})'
    
    # Apply the replacement
    updated_content = re.sub(pattern, replacement, content)
    
    # Count how many replacements were made
    original_matches = len(re.findall(pattern, content))
    updated_matches = len(re.findall(r'fhir_get\(.*?auth_credentials=get_fhir_auth_credentials\(\)', updated_content))
    
    print(f"Found {original_matches} fhir_get calls to update")
    print(f"Updated content now has {updated_matches} calls with auth_credentials")
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print(f"Updated {file_path}")

if __name__ == "__main__":
    update_fhir_get_calls('app.py')
