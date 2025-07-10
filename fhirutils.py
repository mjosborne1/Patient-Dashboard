import os
import requests
from datetime import datetime
from dotenv import load_dotenv

def fhir_get(path, fhir_server_url=None, **kwargs):
    """
    Wrapper for requests.get that includes FHIR server BASIC auth.
    path: the endpoint path, e.g. '/Patient?_count=10'
    fhir_server_url: full base URL for AU Core, e.g. 'https://smile.sparked-fhir.com/aucore/fhir/DEFAULT'
    """
    USE_AUTH = os.environ.get('USER_AUTH')
    FHIR_USERNAME = os.environ.get('FHIR_USERNAME')
    FHIR_PASSWORD = os.environ.get('FHIR_PASSWORD')
    auth = (FHIR_USERNAME, FHIR_PASSWORD) if FHIR_USERNAME and FHIR_PASSWORD else None
    base_url = fhir_server_url or os.environ.get('FHIR_SERVER_URL')
    url = ''
    if base_url:
        url = base_url.rstrip('/') + '/' + path.lstrip('/')
    
    if USE_AUTH and auth != None:
        print(f'Attempting get {url} using auth {auth}')
        return requests.get(url, auth=auth, **kwargs)
    else:
        print(f'Attempting get {url} with no auth')
        return requests.get(url, **kwargs)

def format_fhir_date(date_str, fmt="D"):
    """
    Takes a FHIR date or datetime string and returns a formatted date.
    - fmt="D": returns 'YYYY-MM-DD'
    - fmt="DT": returns 'YYYY-MM-DD HH:MM'
    Handles both 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SS' formats.
    Returns the original string if parsing fails or input is empty.
    """
    if not date_str:
        return ''
    try:
        if 'T' in date_str:
            dt = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S')
            if fmt == "DT":
                return dt.strftime('%Y-%m-%d %H:%M')
            else:
                return dt.strftime('%Y-%m-%d')
        else:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d')
    except ValueError:
        return date_str
    
def get_text_display(codeable_concept, default="Unknown"):
    """
    Returns the best display string for a FHIR CodeableConcept.
    - Prefers the first coding.display, then text, else default.
    """
    if not codeable_concept:
        return default
    # Try coding.display
    codings = codeable_concept.get('coding', [])
    for coding in codings:
        if coding.get('display'):
            return coding['display']
    # Try text
    if codeable_concept.get('text'):
        return codeable_concept['text']
    return default

def find_category(categories, system, code):
    """
    Returns True if any coding in any category matches the given system and code.
    categories: list of category dicts (each with 'coding' list)
    system: string, e.g. "http://terminology.hl7.org/CodeSystem/observation-category"
    code: string, e.g. "laboratory"
    """
    if not categories:
        return False
    for cat in categories:
        for coding in cat.get('coding', []):
            if coding.get('system') == system and coding.get('code') == code:
                return True
    return False