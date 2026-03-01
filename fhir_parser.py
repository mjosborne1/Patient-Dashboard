"""
FHIR Bundle Parser Module

Handles parsing of FHIR Bundle dictionaries and extraction of resources and their codes.
Adapted from fhir-bundle-viz for use in Patient Dashboard.
"""

import json
from typing import Dict, Any, List, Optional


def extract_resources(bundle: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Extract all resources from a FHIR Bundle and index them by ID.
    
    Args:
        bundle: Parsed FHIR Bundle dictionary
        
    Returns:
        Dictionary mapping resource IDs to resource objects with metadata
        Format: {resource_id: {'resource': {...}, 'fullUrl': '...', 'id': '...'}}
    """
    resources = {}
    entries = bundle.get('entry', [])
    
    for entry in entries:
        resource = entry.get('resource')
        full_url = entry.get('fullUrl', '')
        
        if not resource:
            continue
            
        resource_id = get_resource_id(resource, full_url)
        resources[resource_id] = {
            'resource': resource,
            'fullUrl': full_url,
            'id': resource_id
        }
    
    return resources


def get_resource_id(resource: Dict[str, Any], full_url: str) -> str:
    """
    Extract a unique identifier for a resource.
    
    Args:
        resource: FHIR resource dictionary
        full_url: The fullUrl from the Bundle entry
        
    Returns:
        Resource identifier (UUID or resource.id)
    """
    # Try to extract UUID from fullUrl (e.g., "urn:uuid:12345" -> "12345")
    if full_url.startswith('urn:uuid:'):
        return full_url.replace('urn:uuid:', '')
    
    # Fall back to resource.id if present
    if 'id' in resource:
        return resource['id']
    
    # Last resort: use the full URL
    return full_url


def extract_code_display(resource: Dict[str, Any]) -> Optional[str]:
    """
    Extract category and code information from a FHIR resource.
    
    Format as: "Category - Code: Display"
    
    Args:
        resource: FHIR resource dictionary
        
    Returns:
        Formatted code display string or None if no code found
    """
    parts = []
    
    # Extract category (if present)
    category_text = _extract_category(resource)
    if category_text:
        parts.append(category_text)
    
    # Extract code
    code_text = _extract_code(resource)
    if code_text:
        parts.append(code_text)
    
    if not parts:
        return None
    
    if len(parts) == 2:
        return f"{parts[0]} - {parts[1]}"
    else:
        return parts[0]


def _extract_category(resource: Dict[str, Any]) -> Optional[str]:
    """Extract category from a resource (if present)."""
    categories = resource.get('category', [])
    
    if not categories:
        return None
    
    # Take the first category
    if isinstance(categories, list) and len(categories) > 0:
        category = categories[0]
    else:
        category = categories
    
    if not isinstance(category, dict):
        return None
    
    return _extract_codeable_concept(category)


def _extract_code(resource: Dict[str, Any]) -> Optional[str]:
    """Extract code from a resource."""
    code = resource.get('code')
    
    if not code:
        code = resource.get('type')
    
    if not code:
        return None
    
    return _extract_codeable_concept(code)


def _extract_codeable_concept(codeable_concept: Dict[str, Any]) -> Optional[str]:
    """
    Extract display text from a CodeableConcept.
    
    Priority:
    1. coding[].code + coding[].display (formatted as "code: display")
    2. text field (fallback)
    """
    if not isinstance(codeable_concept, dict):
        return None
    
    # Try to get from coding array
    codings = codeable_concept.get('coding', [])
    if codings and isinstance(codings, list) and len(codings) > 0:
        coding = codings[0]
        code = coding.get('code', '')
        display = coding.get('display', '')
        
        if code and display:
            return f"{code}: {display}"
        elif display:
            return display
        elif code:
            return code
    
    # Fallback to text field
    text = codeable_concept.get('text')
    if text:
        return text
    
    return None


def is_task_group(resource: Dict[str, Any]) -> bool:
    """
    Check whether a Task resource is a group fulfillment task.
    """
    if resource.get('resourceType') != 'Task':
        return False

    meta = resource.get('meta', {})
    tags = meta.get('tag', [])
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict) and tag.get('code') == 'fulfilment-task-group':
                return True

    return False


def get_task_group_label(resource: Dict[str, Any]) -> str:
    """
    Build a display label for a group Task including Placer Group number.
    """
    group_identifier = resource.get('groupIdentifier', {})
    if isinstance(group_identifier, dict):
        value = group_identifier.get('value', '')
        if value:
            return f"Task Group: Placer Group {value}"

    return "Task Group"


def get_resource_type_display(resource: Dict[str, Any]) -> str:
    """
    Get a display name for the resource including its type and code.
    
    Args:
        resource: FHIR resource dictionary
        
    Returns:
        Display string in format "ResourceType: Code Display" or just "ResourceType"
    """
    resource_type = resource.get('resourceType', 'Unknown')
    code_display = extract_code_display(resource)
    
    if code_display:
        return f"{resource_type}: {code_display}"
    else:
        # For resources without code/category, try to get a meaningful identifier
        if resource_type == 'Patient':
            name = _get_patient_name(resource)
            if name:
                return f"Patient: {name}"
        
        if resource_type == 'Organization':
            org_name = resource.get('name', '')
            if org_name:
                return f"Organization: {org_name}"
        
        if resource_type == 'Encounter':
            enc_class = resource.get('class', {})
            if isinstance(enc_class, dict):
                display = enc_class.get('display', enc_class.get('code', ''))
                if display:
                    return f"Encounter: {display}"
        
        return resource_type


def _get_patient_name(patient: Dict[str, Any]) -> Optional[str]:
    """Extract patient name from Patient resource."""
    names = patient.get('name', [])
    if names and isinstance(names, list) and len(names) > 0:
        name = names[0]
        given = name.get('given', [])
        family = name.get('family', '')
        
        parts = []
        if given:
            parts.extend(given)
        if family:
            parts.append(family)
        
        if parts:
            return ' '.join(parts)
    
    return None
