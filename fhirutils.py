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
    FHIR_USERNAME = os.environ.get('FHIR_USERNAME')
    FHIR_PASSWORD = os.environ.get('FHIR_PASSWORD')
    auth = (FHIR_USERNAME, FHIR_PASSWORD) if FHIR_USERNAME and FHIR_PASSWORD else None
    base_url = fhir_server_url or os.environ.get('FHIR_SERVER_URL')
    url = ''
    if base_url:
        url = base_url.rstrip('/') + '/' + path.lstrip('/')
    return requests.get(url, auth=auth, **kwargs)

def format_fhir_date(date_str):
    """
    Takes a FHIR date or datetime string and returns a formatted date (YYYY-MM-DD).
    Handles both 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SS' formats.
    Returns the original string if parsing fails or input is empty.
    """
    if not date_str:
        return ''
    try:
        if 'T' in date_str:
            # Handles datetime with or without timezone
            return datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
        else:
            return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return date_str