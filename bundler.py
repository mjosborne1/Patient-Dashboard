# Using the form data passed in from form_data = get_form_data(request) in create_diagnostic_request_bundle():
# Create a ServiceRequest Transaction Bundle that includes the following resources:
#    - all ServiceRequests in an Order Episode
#    - Patient (subject)
#.   - coverage as contained resources
#.   - Encounter
#.   - Practitioner
#    - Practitionerrole
#    - Location
#.   - Tasks for each ServiceRequest
#.   - Task group 
#.   - CommunicationRequest for copy-to another recipient
#.   - Consent (MHRConsent Withdrawl profile)
#.   - DocumentReference for Clinical notes

import uuid
import datetime
import logging
from json import dumps
import ast
import os
from fhirutils import fhir_get
import base64
from fhirclient.models import bundle, servicerequest, patient, encounter, practitioner, practitionerrole
from fhirclient.models import location, task, communicationrequest, consent, documentreference, coverage

def generate_narrative_text(resource):
    """
    Generate a simple narrative text for a FHIR resource.
    
    Args:
        resource (dict): The FHIR resource
        
    Returns:
        dict: Narrative object with status and div
    """
    resource_type = resource.get("resourceType", "")
    narrative_text = f"<div xmlns=\"http://www.w3.org/1999/xhtml\"><h3>{resource_type}</h3>"
    
    # Helper function to extract display value from coding
    def get_display_value(value):
        if isinstance(value, dict):
            if "coding" in value and isinstance(value["coding"], list) and len(value["coding"]) > 0:
                return value["coding"][0].get("display", value["coding"][0].get("code", ""))
            elif "text" in value:
                return value["text"]
            elif "display" in value:
                return value["display"]
        elif isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], dict) and "coding" in value[0]:
                return get_display_value(value[0])
        return str(value) if value else ""
    
    # Generate narrative based on resource type
    if resource_type == "ServiceRequest":
        status = resource.get("status", "")
        intent = resource.get("intent", "")
        code_display = get_display_value(resource.get("code", {}))
        category_display = get_display_value(resource.get("category", [{}])[0] if resource.get("category") else {})
        
        narrative_text += f"<p><strong>Status:</strong> {status}</p>"
        narrative_text += f"<p><strong>Intent:</strong> {intent}</p>"
        narrative_text += f"<p><strong>Test:</strong> {code_display}</p>"
        if category_display:
            narrative_text += f"<p><strong>Category:</strong> {category_display}</p>"
        
        # Add sequence if available
        extensions = resource.get("extension", [])
        for ext in extensions:
            if ext.get("url") == "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-displaysequence":
                sequence = ext.get("valueInteger", "")
                narrative_text += f"<p><strong>Sequence:</strong> {sequence}</p>"
        
        # Add reasons if available
        reason_codes = resource.get("reasonCode", [])
        if reason_codes:
            reasons = [get_display_value(reason) for reason in reason_codes]
            narrative_text += f"<p><strong>Reasons:</strong> {', '.join(reasons)}</p>"
    
    elif resource_type == "Encounter":
        status = resource.get("status", "")
        class_display = get_display_value(resource.get("class", {}))
        
        narrative_text += f"<p><strong>Status:</strong> {status}</p>"
        narrative_text += f"<p><strong>Class:</strong> {class_display}</p>"
    
    elif resource_type == "Task":
        status = resource.get("status", "")
        intent = resource.get("intent", "")
        description = resource.get("description", "")
        
        narrative_text += f"<p><strong>Status:</strong> {status}</p>"
        narrative_text += f"<p><strong>Intent:</strong> {intent}</p>"
        if description:
            narrative_text += f"<p><strong>Description:</strong> {description}</p>"
    
    elif resource_type == "DocumentReference":
        status = resource.get("status", "")
        type_display = get_display_value(resource.get("type", {}))
        
        narrative_text += f"<p><strong>Status:</strong> {status}</p>"
        narrative_text += f"<p><strong>Type:</strong> {type_display}</p>"
        
        # Add content info
        content = resource.get("content", [])
        if content and len(content) > 0:
            attachment = content[0].get("attachment", {})
            title = attachment.get("title", "")
            content_type = attachment.get("contentType", "")
            if title:
                narrative_text += f"<p><strong>Title:</strong> {title}</p>"
            if content_type:
                narrative_text += f"<p><strong>Content Type:</strong> {content_type}</p>"
    
    elif resource_type == "CommunicationRequest":
        status = resource.get("status", "")
        narrative_text += f"<p><strong>Status:</strong> {status}</p>"
        narrative_text += f"<p>Request for communication regarding patient care.</p>"
    
    elif resource_type == "Consent":
        status = resource.get("status", "")
        scope_display = get_display_value(resource.get("scope", {}))
        category_display = get_display_value(resource.get("category", [{}])[0] if resource.get("category") else {})
        
        narrative_text += f"<p><strong>Status:</strong> {status}</p>"
        if scope_display:
            narrative_text += f"<p><strong>Scope:</strong> {scope_display}</p>"
        if category_display:
            narrative_text += f"<p><strong>Category:</strong> {category_display}</p>"
        
        provision = resource.get("provision", {})
        if provision:
            provision_type = provision.get("type", "")
            narrative_text += f"<p><strong>Provision:</strong> {provision_type}</p>"
    
    elif resource_type == "Coverage":
        status = resource.get("status", "")
        type_display = get_display_value(resource.get("type", {}))
        
        narrative_text += f"<p><strong>Status:</strong> {status}</p>"
        if type_display:
            narrative_text += f"<p><strong>Type:</strong> {type_display}</p>"
    
    narrative_text += "</div>"
    
    return {
        "status": "generated",
        "div": narrative_text
    }

def create_request_bundle(form_data, fhir_server_url=None):
    """
    Creates a FHIR Transaction Bundle for diagnostic requests based on form data.
    
    Args:
        form_data (dict): The processed form data from the request containing patient_id
        
    Returns:
        dict: A FHIR Bundle resource with type 'transaction' containing all required resources
    """
    
    logging.info("Starting bundle creation process")
    try:
        logging.debug(f"Form data received: {dumps(form_data, indent=2, default=str)}")
    except (TypeError, ValueError) as e:
        logging.debug(f"Form data received (raw): {form_data}")
        logging.warning(f"Could not serialize form_data to JSON: {e}")
    
    # Get timestamp in BNE time
    def get_localtime_bne():
        """Helper function to get timestamp in UTC+10:00 timezone"""
        utc_time = datetime.datetime.utcnow()
        # Add 10 hours to UTC
        utc_plus_10 = utc_time + datetime.timedelta(hours=10)
        # Format with timezone indicator
        return utc_plus_10.strftime("%Y-%m-%dT%H:%M:%S.%f+10:00")
    
    # Extract patient_id from form_data
    patient_id = form_data.get('patient_id', '')
    if not patient_id:
        raise ValueError("Patient ID is required but was not found in form_data")
    
    # Create a Bundle with type "transaction"
    bundle_id = str(uuid.uuid4())
    transaction_bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "transaction",
        "entry": []
    }

    # Add timestamp
    transaction_bundle["timestamp"] = get_localtime_bne()
    
    # Get request category (Pathology or Radiology)
    request_category = form_data.get('requestCategory', 'Pathology')
    
    # Inside create_request_bundle function, update the test data handling:

    # Extract test and reason data
    tests = form_data.get('selectedTests', [])
    if isinstance(tests, str):
        try:
            # Try to safely parse the string representation to a list
            import json
            tests = json.loads(tests)
        except json.JSONDecodeError:
            # If it's not valid JSON, try a more forgiving approach
            try:
                import ast
                tests = ast.literal_eval(tests)
            except (ValueError, SyntaxError):
                tests = []

    # Ensure each test is a dictionary with the required keys
    processed_tests = []
    for test in tests:
        if isinstance(test, dict) and "code" in test and "display" in test:
            processed_tests.append(test)
        elif isinstance(test, str):
            # If it's just a string (perhaps just the display name), create a simple dict
            processed_tests.append({"code": "", "display": test})
        else:
            # Log unexpected test format
            logging.warning(f"Skipping invalid test format: {test}")

    # Replace original tests list with processed version
    tests = processed_tests
            
    reasons = form_data.get('selectedReasons', [])
    logging.debug(f"Raw selectedReasons from form: {reasons}")
    
    if isinstance(reasons, str):
        try:
            # Try to safely parse the string representation to a list
            import json
            reasons = json.loads(reasons)
            logging.debug("Successfully parsed reasons as JSON")
        except json.JSONDecodeError:
            # If it's not valid JSON, try a more forgiving approach
            try:
                reasons = ast.literal_eval(reasons)
                logging.debug("Successfully parsed reasons using ast.literal_eval")
            except (ValueError, SyntaxError):
                logging.warning("Failed to parse reasons string, defaulting to empty list")
                reasons = []

    # Ensure each reason is a dictionary with the required keys
    processed_reasons = []
    for i, reason in enumerate(reasons):
        if isinstance(reason, dict) and "code" in reason and "display" in reason:
            processed_reasons.append(reason)
            logging.debug(f"Reason {i}: {reason['display']} ({reason['code']})")
        elif isinstance(reason, str):
            # If it's just a string (perhaps just the display name), create a simple dict
            processed_reasons.append({"code": "", "display": reason})
            logging.warning(f"Reason {i}: Converting string '{reason}' to dict with empty code")
        else:
            # Log unexpected reason format
            logging.warning(f"Skipping invalid reason format at index {i}: {reason}")

    # Replace original reasons list with processed version
    reasons = processed_reasons
    logging.info(f"Processing {len(reasons)} reasons")
    
    # Get requester info
    requester_id = form_data.get('requester', '')
    
    # Get organization info
    organization_id = form_data.get('organisation', '')
    
    # Create and add Patient reference (assumed to exist already)
    patient_reference = {
        "reference": f"Patient/{patient_id}"
    }
    
    # Create and add reference to Practitioner (requester)
    practitioner_reference = None
    if requester_id:
        practitioner_reference = {
            "reference": f"PractitionerRole/{requester_id}"
        }
        
        # Fetch and add PractitionerRole resource to the bundle
        try:
            server_url = fhir_server_url or os.environ.get('FHIR_SERVER_URL', 'https://aucore.aidbox.beda.software/fhir')
            response = fhir_get(f"/PractitionerRole/{requester_id}?_include=PractitionerRole:practitioner", 
                              fhir_server_url=server_url, timeout=10)
            if response.status_code == 200:
                practitioner_role_data = response.json()
                if practitioner_role_data.get('resourceType') == 'PractitionerRole':
                    # Add PractitionerRole resource to bundle
                    transaction_bundle["entry"].append({
                        "fullUrl": f"urn:uuid:{str(uuid.uuid4())}",
                        "resource": practitioner_role_data,
                        "request": {
                            "method": "PUT",
                            "url": f"PractitionerRole/{requester_id}"
                        }
                    })
                    
                    # If the response includes a practitioner, add it too
                    if practitioner_role_data.get('entry'):
                        for entry in practitioner_role_data.get('entry', []):
                            resource = entry.get('resource', {})
                            if resource.get('resourceType') == 'Practitioner':
                                practitioner_id = resource.get('id')
                                transaction_bundle["entry"].append({
                                    "fullUrl": f"urn:uuid:{str(uuid.uuid4())}",
                                    "resource": resource,
                                    "request": {
                                        "method": "PUT",
                                        "url": f"Practitioner/{practitioner_id}"
                                    }
                                })
                elif practitioner_role_data.get('resourceType') == 'Bundle':
                    # Handle bundle response with _include
                    for entry in practitioner_role_data.get('entry', []):
                        resource = entry.get('resource', {})
                        if resource.get('resourceType') == 'PractitionerRole':
                            transaction_bundle["entry"].append({
                                "fullUrl": f"urn:uuid:{str(uuid.uuid4())}",
                                "resource": resource,
                                "request": {
                                    "method": "PUT",
                                    "url": f"PractitionerRole/{requester_id}"
                                }
                            })
                        elif resource.get('resourceType') == 'Practitioner':
                            practitioner_id = resource.get('id')
                            transaction_bundle["entry"].append({
                                "fullUrl": f"urn:uuid:{str(uuid.uuid4())}",
                                "resource": resource,
                                "request": {
                                    "method": "PUT",
                                    "url": f"Practitioner/{practitioner_id}"
                                }
                            })
            else:
                # If response status is not 200, fall back to GET request
                print(f"Failed to fetch PractitionerRole {requester_id}, status: {response.status_code}")
                transaction_bundle["entry"].append({
                    "fullUrl": f"urn:uuid:{str(uuid.uuid4())}",
                    "request": {
                        "method": "GET",
                        "url": f"PractitionerRole/{requester_id}"
                    }
                })
        except Exception as e:
            print(f"Failed to fetch PractitionerRole {requester_id}: {e}")
            # Fall back to GET request if fetch fails
            transaction_bundle["entry"].append({
                "fullUrl": f"urn:uuid:{str(uuid.uuid4())}",
                "request": {
                    "method": "GET",
                    "url": f"PractitionerRole/{requester_id}"
                }
            })
    
    # Create and add reference to Organization (if provided)
    organization_reference = None
    if organization_id:
        organization_reference = {
            "reference": f"Organization/{organization_id}"
        }
        
        # Add Organization as a GET request in the bundle
        transaction_bundle["entry"].append({
            "fullUrl": f"urn:uuid:{str(uuid.uuid4())}",
            "request": {
                "method": "GET",
                "url": f"Organization/{organization_id}"
            }
        })
    
    # Generate a unique requisition number for this order (8 digits starting with current year)
    current_year = datetime.datetime.now().year % 100  # Get last 2 digits of year (e.g., 25 for 2025)
    import random
    requisition_number = f"{current_year:02d}-{random.randint(100000, 999999)}"
    logging.info(f"Generated requisition number: {requisition_number}")
    
    # Generate task group ID early so individual tasks can reference it
    group_task_id = str(uuid.uuid4())
    
    # Create supporting resources first (before ServiceRequests that reference them)
    pregnancy_obs_id = None
    doc_ref_id = None
    
    # Create Pregnancy Observation if pregnancy status is indicated
    is_pregnant = form_data.get('isPregnant', False)
    if is_pregnant == 'true' or is_pregnant is True:
        pregnancy_obs_id = str(uuid.uuid4())
        
        pregnancy_obs = {
            "resourceType": "Observation",
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/uv/ips/StructureDefinition/Observation-pregnancy-status-uv-ips"
                ]
            },
            "id": pregnancy_obs_id,
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "exam",
                    "display": "Exam"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "77386006",
                    "display": "Pregnancy"
                }]
            },
            "subject": patient_reference,
            "effectiveDateTime": get_localtime_bne(),
            "valueCodeableConcept": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "77386006",
                    "display": "Pregnant"
                }]
            }
        }
        
        # Add Pregnancy Observation to bundle
        transaction_bundle["entry"].append({
            "fullUrl": f"urn:uuid:{pregnancy_obs_id}",
            "resource": pregnancy_obs,
            "request": {
                "method": "POST",
                "url": "Observation"
            }
        })
    
    # Create DocumentReference for clinical notes if provided
    clinical_context = form_data.get('clinicalContext', '')
    if clinical_context:
        doc_ref_id = str(uuid.uuid4())
        
        # Base64 encode the clinical context
        encoded_notes = base64.b64encode(clinical_context.encode('utf-8')).decode('utf-8')
        
        doc_ref = {
            "resourceType": "DocumentReference",
            "id": doc_ref_id,
            "status": "current",
            "type": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "34109-9",
                    "display": "Note"
                }]
            },
            "subject": patient_reference,
            "date": get_localtime_bne(),
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data": encoded_notes,
                    "title": "Clinical Context"
                }
            }]
        }
        
        # Add DocumentReference to bundle
        transaction_bundle["entry"].append({
            "fullUrl": f"urn:uuid:{doc_ref_id}",
            "resource": doc_ref,
            "request": {
                "method": "POST",
                "url": "DocumentReference"
            }
        })
    
    # Create a ServiceRequest for each test
    service_requests = []
    for i, test in enumerate(tests):
        sr_id = str(uuid.uuid4())
        encounter_id = str(uuid.uuid4())  # Generate unique encounter ID for each ServiceRequest
        # Set appropriate profile based on request category
        service_request_profile = "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-servicerequest-path"
        if request_category == "Radiology":
            service_request_profile = "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-servicerequest-imag"
        
        # Create ServiceRequest
        service_request = {
            "resourceType": "ServiceRequest",
             "meta": {
                "profile": [
                    service_request_profile
                ]
            },
            "contained": [
                {
                    "resourceType": "Encounter",
                    "meta": {
                        "profile": [
                            "http://hl7.org.au/fhir/core/StructureDefinition/au-core-encounter"
                        ]
                    },
                    "id": encounter_id,
                    "status": "planned",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                        "display": "ambulatory"
                    },
                    "subject": patient_reference
                }
            ],
            "extension": [
                {
                    "url": "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-displaysequence",
                    "valueInteger": test.get("display_sequence",1)
                }
            ],
            "id": sr_id,
            "identifier": [{
                "use": "usual",
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "PLAC",
                        "display": "Placer Identifier"
                    }]
                },
                "system": "http://myclinic.example.org.au/identifier",
                "value": f"{requisition_number}-{test.get('display_sequence', 1)}"
            }],
            "status": "active",
            "intent": "order",
            "requisition": {
                "use": "usual",
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "PGN",
                        "display": "Placer Group Number"
                    }]
                },
                "system": "http://myclinic.example.org.au/identifier",
                "value": requisition_number
            },
            "category": [{
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "108252007" if request_category == "Pathology" else "363679005",
                    "display": "Laboratory procedure" if request_category == "Pathology" else "Imaging"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": test.get("code", ""),
                    "display": test.get("display", "")
                }],
                "text": test.get("display", "")
            },
            "subject": patient_reference,
            "encounter": {
                "reference": f"#{encounter_id}",
                "type": "Encounter"
            },
            "authoredOn": get_localtime_bne()
        }
        
        # Add requester if available
        if practitioner_reference:
            service_request["requester"] = practitioner_reference
            
        # Add performer (organization) if available
        if organization_reference:
            service_request["performer"] = [organization_reference]
            
        # Add reasons if available
        if reasons:
            reason_list = []
            for reason in reasons:
                reason_list.append({
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": reason.get("code", ""),
                        "display": reason.get("display", "")
                    }]
                })
            
            if reason_list:
                service_request["reasonCode"] = reason_list
        
        # Prepare supportingInfo array
        supporting_info = []
        
        # Check if pregnancy status should be added
        if pregnancy_obs_id:
            supporting_info.append({
                "reference": f"urn:uuid:{pregnancy_obs_id}",
                "display": "Pregnancy status"
            })
        
        # Check if clinical context DocumentReference should be added
        if doc_ref_id:
            supporting_info.append({
                "reference": f"urn:uuid:{doc_ref_id}",
                "display": "Clinical Context"
            })
        
        # Add supportingInfo to ServiceRequest if we have any
        if supporting_info:
            service_request["supportingInfo"] = supporting_info
                
        # Add ServiceRequest to bundle
        transaction_bundle["entry"].append({
            "fullUrl": f"urn:uuid:{sr_id}",
            "resource": service_request,
            "request": {
                "method": "POST",
                "url": "ServiceRequest"
            }
        })
        
        service_requests.append(service_request)
        
        # Create Task for this ServiceRequest
        task_id = str(uuid.uuid4())
        task = {
            "resourceType": "Task",
            "meta": {
                "profile": [
                    "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-task-diagnosticrequest"
                ],
                "tag": [
                    {
                        "system": "http://terminology.hl7.org.au/CodeSystem/resource-tag",
                        "code": "fulfilment-task"
                    }
                ]
            },
            "id": task_id,
            "groupIdentifier": {
                "use": "usual",
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "PGN",
                        "display": "Placer Group Number"
                    }]
                },
                "system": "http://myclinic.example.org.au/identifier",
                "value": requisition_number
            },
            "status": "requested",
            "intent": "order",
            "focus": {
                "reference": f"urn:uuid:{sr_id}"
            },
            "for": patient_reference,
            # supportingInfo goes here
            "requester": practitioner_reference if practitioner_reference else {"reference": "PractitionerRole/unknown"},
            "owner": organization_reference if organization_reference else {"reference": "Organization/unknown"},
            "partOf": [{
                "reference": f"urn:uuid:{group_task_id}"
            }],
            "authoredOn": get_localtime_bne()
        }
        
        # Add Task to bundle
        transaction_bundle["entry"].append({
            "fullUrl": f"urn:uuid:{task_id}",
            "resource": task,
            "request": {
                "method": "POST",
                "url": "Task"
            }
        })
    
    # Create a Task group that references all ServiceRequests
    if service_requests:
        task_group = {
            "resourceType": "Task",
            "meta": {
                "profile": [
                    "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-task-group"
                ],
                "tag": [
                    {
                        "system": "http://terminology.hl7.org.au/CodeSystem/resource-tag",
                        "code": "fulfilment-task-group"
                    }
                ]
            },
            "id": group_task_id,
            "groupIdentifier": {
                "use": "usual",
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "PGN",
                        "display": "Placer Group Number"
                    }]
                },
                "system": "http://myclinic.example.org.au/identifier",
                "value": requisition_number
            },
            "status": "requested",
            "intent": "order",
            "description": f"{request_category} Order Group",
            "for": patient_reference,
            "requester": practitioner_reference if practitioner_reference else {"reference": "PractitionerRole/unknown"},
            "owner": organization_reference if organization_reference else {"reference": "Organization/unknown"},
            "authoredOn": get_localtime_bne()
        }
            
        # Add Task group to bundle
        transaction_bundle["entry"].append({
            "fullUrl": f"urn:uuid:{group_task_id}",
            "resource": task_group,
            "request": {
                "method": "POST",
                "url": "Task"
            }
        })
    
    # Add CommunicationRequest for copy-to recipients (if provided)
    copy_to_recipients = form_data.get('copyTo', [])
    if copy_to_recipients:
        # Handle case where copyTo might be a JSON string (from new typeahead) or list (multiple values)
        if isinstance(copy_to_recipients, str):
            try:
                # Try to parse as JSON first (from typeahead implementation)
                import json
                copy_to_recipients = json.loads(copy_to_recipients)
            except json.JSONDecodeError:
                # If it's not valid JSON, treat as single value
                copy_to_recipients = [copy_to_recipients] if copy_to_recipients else []
        
        # Create a CommunicationRequest for each recipient
        for recipient_id in copy_to_recipients:
            if recipient_id:  # Skip empty values
                comm_req_id = str(uuid.uuid4())
                comm_req = {
                    "resourceType": "CommunicationRequest",
                    "meta": {
                        "profile": [
                            "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-communicationrequest-copyto"
                        ]
                    },
                    "id": comm_req_id,
                    "groupIdentifier": {
                        "use": "usual",
                        "type": {
                            "coding": [{
                                "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                "code": "PGN",
                                "display": "Placer Group Number"
                            }]
                        },
                        "system": "http://myclinic.example.org.au/identifier",
                        "value": requisition_number
                    },
                    "status": "active",
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/communication-category",
                            "code": "notification"
                        }]
                    }],
                    "subject": patient_reference,
                    "about": [{"reference": f"urn:uuid:{sr['id']}"} for sr in service_requests],
                    "requester": practitioner_reference if practitioner_reference else {"reference": "PractitionerRole/unknown"},
                    "reasonCode": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org.au/CodeSystem/communicationrequest-reason",
                            "code": "copyto"
                        }]
                    }],
                    "recipient": [{
                        "reference": f"PractitionerRole/{recipient_id}"
                    }],
                    "authoredOn": get_localtime_bne()
                }
                
                # Add CommunicationRequest to bundle
                transaction_bundle["entry"].append({
                    "fullUrl": f"urn:uuid:{comm_req_id}",
                    "resource": comm_req,
                    "request": {
                        "method": "POST",
                        "url": "CommunicationRequest"
                    }
                })
                
                # Add PractitionerRole as a GET request in the bundle for each recipient
                transaction_bundle["entry"].append({
                    "fullUrl": f"urn:uuid:{str(uuid.uuid4())}",
                    "request": {
                        "method": "GET",
                        "url": f"PractitionerRole/{recipient_id}"
                    }
                })
    
    # Add Consent (MHR Consent Withdrawal) if user opted out
    consent_opt_out = form_data.get('mhrConsentWithdrawn', False)
    if consent_opt_out:
        consent_id = str(uuid.uuid4())
        consent = {
            "resourceType": "Consent",
            "meta": {
                "profile": [
                    "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-mhrconsentwithdrawal"
                ]
            },
            "id": consent_id,
            "status": "active",
            "scope": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/consentscope",
                    "code": "patient-privacy",
                    "display": "Privacy"
                }]
            },
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/consentcategorycodes",
                    "code": "mhr",
                    "display": "My Health Record consent"
                }]
            }],
            "patient": patient_reference,
            "dateTime": get_localtime_bne(),
            "policy": [{
                "uri": "http://example.org/policies/mhr-consent-withdrawal"
            }],
            "provision": {
                "type": "deny"
            }
        }
        
        # Add Consent to bundle
        transaction_bundle["entry"].append({
            "fullUrl": f"urn:uuid:{consent_id}",
            "resource": consent,
            "request": {
                "method": "POST",
                "url": "Consent"
            }
        })
        
    # Add Coverage as contained resource if provided
    bill_type = form_data.get('billingCategory', '')
    if bill_type:
        # Map billing category codes to their display text
        billing_category_mapping = {
            'PUBLICPOL': 'Medicare',
            'VET': 'Department of Veterans\' Affairs',
            'pay': 'Private Pay',
            'payconc': 'Private Pay with Concession',
            'AUPUBHOSP': 'Public Hospital',
            'WCBPOL': 'Workers\' Compensation'
        }
        
        coverage_id = str(uuid.uuid4())
        coverage = {
            "resourceType": "Coverage",
            "meta": {
                "profile": [
                    "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-coverage"
                ]
            },
            "id": coverage_id,
            "status": "active",
            "type": {
                "coding": [{
                    "code": bill_type
                }],
                "text": billing_category_mapping.get(bill_type, bill_type)
            },
            "beneficiary": patient_reference,
            "payor": [{
                "display": billing_category_mapping.get(bill_type, bill_type)
            }]
        }
        
        # Add Coverage to bundle
        transaction_bundle["entry"].append({
            "fullUrl": f"urn:uuid:{coverage_id}",
            "resource": coverage,
            "request": {
                "method": "POST",
                "url": "Coverage"
            }
        })
    
    # Add narratives to all resources if requested
    add_narrative = form_data.get('addNarrative', False)
    if add_narrative:
        logging.info("Adding narrative text to all resources")
        for entry in transaction_bundle["entry"]:
            if "resource" in entry:
                resource = entry["resource"]
                narrative = generate_narrative_text(resource)
                resource["text"] = narrative
    
    return transaction_bundle
