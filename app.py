from flask import Flask, g, render_template, jsonify, request, session, redirect, url_for, make_response
import requests
import json
import logging
from flask_login import LoginManager, AnonymousUserMixin, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
import os  # Add os module for environment variables
from fhirpathpy import evaluate
from fhirutils import fhir_get, format_fhir_date, get_text_display, find_category, get_form_data
from bundler import create_request_bundle


app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for Flask session management

login_manager = LoginManager()
login_manager.init_app(app)


# Set up logging
logging.basicConfig(level=logging.INFO)

# User model for Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id # wallet_address will be the id

    @staticmethod
    def get(user_id):
        # This is a simplified 'get' method. In a real app, you might query a database.
        # For this example, if a user_id is provided, we create a User object.
        # Flask-Login uses this to manage the user session.
        return User(user_id)

# Mock user for always-authenticated sessions
class MockUser(UserMixin):
    def __init__(self):
        self.id = "mockuser"

    @property
    def is_authenticated(self):
        return True
    
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Automatically log in the mock user for every request
@app.before_request
def auto_login():
    from flask_login import login_user, current_user
    if not current_user.is_authenticated:
        login_user(MockUser())

def get_fhir_server_url():
    # Try to get from custom header (set by frontend from localStorage), fallback to default
    url = request.headers.get('X-FHIR-Server-URL')
    if not url:
        url = os.environ.get('FHIR_SERVER_URL', 'https://aucore.aidbox.beda.software/fhir')
    return url

def get_fhir_auth_credentials():
    # Try to get from custom headers (set by frontend from localStorage), fallback to env vars
    username = request.headers.get('X-FHIR-Username')
    password = request.headers.get('X-FHIR-Password')
    
    if not username or not password:
        username = os.environ.get('FHIR_USERNAME')
        password = os.environ.get('FHIR_PASSWORD')
    
    if username and password:
        return (username, password)
    return None

@app.route('/')
def index():
    # Redirect unauthenticated users to the dedicated login page
    # if not current_user.is_authenticated:
    #     return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Simple health check endpoint for monitoring"""
    fhir_server_url = get_fhir_server_url()
    return jsonify({"status": "ok", "fhir_server": fhir_server_url})

@app.route('/test-datalist')
def test_datalist():
    """Test page for debugging datalist HTMX behavior"""
    with open('test_datalist.html', 'r') as f:
        return f.read()

def process_patient_results(patients):
    """Process patient results for consistent display"""
    processed_patients = []
    
    for patient_entry in patients:
        resource = patient_entry['resource']

        # Extract name
        name = resource.get('name', [{'given': ['Unknown'], 'family': ''}])[0]
        full_name = ' '.join(name.get('given', ['Unknown']) + [name.get('family', '')])

        # Extract gender
        gender = resource.get('gender', 'Unknown')

        # Extract birth date
        birth_date = resource.get('birthDate', 'Unknown')

        # Extract address
        address_info = resource.get('address', [{'line': ['Unknown Address']}])[0]
        address_parts = address_info.get('line', [])
        address_parts.extend([
            address_info.get('city', ''),
            address_info.get('state', ''),
            address_info.get('postalCode', '')
        ])
        address = ', '.join(filter(None, address_parts))  # Filter out empty strings

        # Extract telecom
        telecom_info = resource.get('telecom', [{'value': 'Unknown Contact'}])[0]
        telecom = telecom_info.get('value', 'Unknown Contact')

        processed_patient = {
            "id": resource.get('id', 'Unknown'),
            "name": full_name,
            "gender": gender,
            "birthDate": birth_date,
            "address": address,
            "telecom": telecom,
        }

        processed_patients.append(processed_patient)
        
    return processed_patients

def get_patients_table_body():
    """Helper to get patient table body for reuse"""
    response = fhir_get("/Patient?_count=10", fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
    if response.status_code == 200:
        patients = response.json().get('entry', [])
        processed_patients = process_patient_results(patients)
        return render_template('patient_table_body.html', patients=processed_patients)
    else:
        return "<tr><td colspan='7'>Error loading patients</td></tr>", 500

def probe_for_total_count(current_page, per_page):
    """
    Attempt to find the actual total count by probing for the last page.
    Uses a binary search approach to efficiently find where the data ends.
    """
    try:
        # Start with a reasonable upper bound (e.g., 10 pages = 100 patients)
        max_pages_to_check = 10
        
        # Quick check: try a few pages ahead to see if they exist
        for probe_page in [current_page + 1, current_page + 2, current_page + 5]:
            if probe_page > max_pages_to_check:
                break
                
            offset = (probe_page - 1) * per_page
            probe_url = f"/Patient?_count={per_page}&_offset={offset}"
            
            response = fhir_get(probe_url, fhir_server_url=get_fhir_server_url(), 
                               auth_credentials=get_fhir_auth_credentials(), timeout=5)
            
            if response.status_code == 200:
                bundle = response.json()
                entries = bundle.get('entry', [])
                
                if len(entries) == 0:
                    # Found the end! Total is everything before this page
                    total = (probe_page - 1) * per_page
                    logging.info(f"Probed end at page {probe_page}, calculated total: {total}")
                    return total
                elif len(entries) < per_page:
                    # Partial page - this is the last page
                    total = (probe_page - 1) * per_page + len(entries) 
                    logging.info(f"Probed partial page {probe_page}, calculated total: {total}")
                    return total
            else:
                # If we get an error, assume we've hit the end
                total = (probe_page - 1) * per_page
                logging.info(f"Probed error at page {probe_page}, estimated total: {total}")
                return total
        
        # If we didn't find the end within our reasonable bounds, return None
        logging.info(f"Could not determine total within {max_pages_to_check} pages")
        return None
        
    except Exception as e:
        logging.warning(f"Error during total count probe: {e}")
        return None

@app.route('/fhir/Patients')
@login_required
def get_patients():
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search_term = request.args.get('q', '').strip().lower()
    
    logging.info(f"get_patients called with page={page}, per_page={per_page}, search_term='{search_term}', is_htmx={request.headers.get('HX-Request') is not None}")
    
    try:
        auth_creds = get_fhir_auth_credentials()
        server_url = get_fhir_server_url()
        logging.info(f"Using server: {server_url}, auth: {'yes' if auth_creds else 'no'}")
    except Exception as e:
        logging.error(f"Error getting FHIR config: {e}")
        return jsonify({"error": "Configuration error"}), 500
    
    if search_term:
        # Handle search with pagination
        try:
            # For search, we need to fetch more records to filter client-side
            response = fhir_get("/Patient?_count=1000", fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
            if response.status_code == 200:
                patients = response.json().get('entry', [])
                # Filter patients by name (case-insensitive, anywhere in given or family)
                filtered_patients = []
                for entry in patients:
                    resource = entry.get('resource', {})
                    names = resource.get('name', [])
                    for name in names:
                        given_names = ' '.join(name.get('given', []))
                        family_name = name.get('family', '')
                        full_name = f"{given_names} {family_name}".strip().lower()
                        if search_term in full_name:
                            filtered_patients.append(entry)
                            break  # Only need to match one name per patient
                
                # Apply pagination to filtered results (client-side pagination for search)
                skip = (page - 1) * per_page
                total_filtered = len(filtered_patients)
                paginated_patients = filtered_patients[skip:skip + per_page]
                
                processed_patients = process_patient_results(paginated_patients)
                
                # Calculate pagination info for filtered results
                total_pages = max(1, (total_filtered + per_page - 1) // per_page) if total_filtered > 0 else 1
                has_next = page < total_pages and total_filtered > 0
                has_prev = page > 1
                
                # For HTMX requests targeting table body only, return just the table body with pagination info
                # For HTMX requests targeting content or no target specified, return full page
                hx_target = request.headers.get('HX-Target', '')
                if request.headers.get('HX-Request') and 'patients-table-body' in hx_target:
                    response_html = render_template('patient_table_body.html', patients=processed_patients)
                    resp = make_response(response_html)
                    resp.headers['X-Current-Page'] = str(page)
                    resp.headers['X-Total-Pages'] = str(total_pages)
                    resp.headers['X-Total-Items'] = str(total_filtered)
                    resp.headers['X-Per-Page'] = str(per_page)
                    resp.headers['X-Has-Next'] = str(has_next).lower()
                    resp.headers['X-Has-Prev'] = str(has_prev).lower()
                    return resp
                else:
                    return render_template('patients.html', 
                                         patients=processed_patients,
                                         current_page=page,
                                         total_pages=total_pages,
                                         total_items=total_filtered,
                                         per_page=per_page,
                                         has_next=has_next,
                                         has_prev=has_prev)
            else:
                return jsonify({"error": "Failed to search patients"}), 500
        except Exception as e:
            logging.error(f"Error searching patients: {e}")
            return jsonify({"error": "Search failed"}), 500
    else:
        # Regular pagination without search
        # Make FHIR request with pagination using FHIR standard _offset parameter
        try:
            # Try different pagination approaches based on server support
            # Some servers support _offset, others use bundle links, some use custom parameters
            if page == 1:
                # For first page, just use _count
                query_url = f"/Patient?_count={per_page}"
            else:
                # For subsequent pages, try _offset first (FHIR R4 standard)
                offset = (page - 1) * per_page
                query_url = f"/Patient?_count={per_page}&_offset={offset}"
            
            logging.info(f"Making FHIR request: {query_url}")
            response = fhir_get(query_url, fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
            logging.info(f"FHIR response status: {response.status_code}")
            
            # If _offset failed, try to use FHIR link-based pagination
            if response.status_code == 404 and page > 1 and "_offset=" in query_url:
                logging.info(f"_offset not supported - trying FHIR link-based pagination for page {page}")
                
                # Navigate through pagination links to reach the desired page
                current_page = 1
                current_url = f"/Patient?_count={per_page}"
                
                while current_page < page:
                    logging.info(f"Fetching page {current_page} to navigate to page {page}")
                    page_response = fhir_get(current_url, fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
                    
                    if page_response.status_code != 200:
                        return render_template('patients.html', 
                                             patients=[],
                                             current_page=page,
                                             total_pages=1,
                                             total_items=0,
                                             per_page=per_page,
                                             has_next=False,
                                             has_prev=True,
                                             error_message=f"Failed to navigate to page {page}. Could not load page {current_page}.")
                    
                    bundle = page_response.json()
                    bundle_links = bundle.get('link', [])
                    next_link_url = None
                    
                    # Find the next link
                    for link in bundle_links:
                        if link.get('relation') == 'next':
                            next_link_url = link.get('url', '')
                            break
                    
                    if next_link_url:
                        from urllib.parse import urlparse
                        parsed_url = urlparse(next_link_url)
                        if parsed_url.query:
                            current_url = f"/Patient?{parsed_url.query}"
                            current_page += 1
                        else:
                            return render_template('patients.html', 
                                                 patients=[],
                                                 current_page=page,
                                                 total_pages=1,
                                                 total_items=0,
                                                 per_page=per_page,
                                                 has_next=False,
                                                 has_prev=True,
                                                 error_message="Invalid FHIR pagination link format.")
                    else:
                        # No next link found - this means we've reached the end
                        return render_template('patients.html', 
                                             patients=[],
                                             current_page=page,
                                             total_pages=current_page,
                                             total_items=0,
                                             per_page=per_page,
                                             has_next=False,
                                             has_prev=True,
                                             error_message=f"Page {page} not available. Only {current_page} pages exist.")
                
                # Now fetch the target page
                query_url = current_url
                logging.info(f"Using FHIR link-based navigation to reach page {page}: {query_url}")
                response = fhir_get(query_url, fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
                logging.info(f"Target page response status: {response.status_code}")
                
                if response.status_code != 200:
                    return render_template('patients.html', 
                                         patients=[],
                                         current_page=page,
                                         total_pages=1,
                                         total_items=0,
                                         per_page=per_page,
                                         has_next=False,
                                         has_prev=True,
                                         error_message=f"Failed to load page {page} using FHIR pagination links.")
            
            if response.status_code == 200:
                bundle = response.json()
                all_patients = bundle.get('entry', [])
                bundle_total = bundle.get('total', None)
                
                # If we fetched extra records for client-side pagination, slice them
                # Only do client-side pagination if we're not using FHIR link-based pagination
                if "_offset=" not in query_url and "page=" not in query_url and page > 1:
                    # Client-side pagination fallback
                    start_idx = (page - 1) * per_page
                    end_idx = start_idx + per_page
                    patients = all_patients[start_idx:end_idx]
                    logging.info(f"Client-side pagination: showing {start_idx}-{end_idx} of {len(all_patients)} records")
                    
                    # For fallback pagination, we need to estimate total more intelligently
                    if bundle_total is not None:
                        # Use server's total if available
                        total = bundle_total
                        logging.info(f"Using server total for fallback: {total} (bundle_total={bundle_total}, len(all_patients)={len(all_patients)})")
                    elif len(all_patients) == per_page * page + per_page or len(all_patients) >= 1000:
                        # We hit our fetch limit, assume there are more records
                        # Use a conservative estimate: at least current page plus one more
                        total = (page + 1) * per_page
                        logging.info(f"Estimated total for fallback (hit limit): {total}")
                    else:
                        # We got fewer records than requested, this might be all of them
                        total = len(all_patients)
                        logging.info(f"Using fetched count for fallback (appears complete): {total}")
                else:
                    # Server-side pagination or first page
                    patients = all_patients
                    
                    # Determine total count for pagination
                    if bundle_total is not None:
                        # Server provided total count - use it directly
                        total = bundle_total
                        logging.info(f"Using server total: {total} (bundle_total={bundle_total}, len(all_patients)={len(all_patients)})")
                    else:
                        # Server didn't provide total - estimate based on pagination cues
                        # Check if there might be more pages by looking for 'next' link or if we got full page
                        bundle_links = bundle.get('link', [])
                        has_next_link = any(link.get('relation') == 'next' for link in bundle_links)
                        
                        if has_next_link or len(all_patients) == per_page:
                            # There are more pages - use a consistent conservative estimate
                            # Based on the server logs, this server has around 94 patients
                            # Use a reasonable fixed upper bound so pagination is consistent
                            estimated_total = 100  # Fixed conservative estimate
                            total = estimated_total
                            logging.info(f"Using fixed estimate total: {total} (page {page})")
                        else:
                            # This appears to be the last page - now we can calculate exact total
                            total = (page - 1) * per_page + len(all_patients)
                            logging.info(f"Calculated total (last page): {total}")
                
                processed_patients = process_patient_results(patients)
                
                # Calculate pagination info
                total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1
                has_next = page < total_pages and total > 0
                has_prev = page > 1
                
                # For HTMX requests targeting table body only, return just the table body with pagination info
                # For HTMX requests targeting content or no target specified, return full page
                hx_target = request.headers.get('HX-Target', '')
                if request.headers.get('HX-Request') and 'patients-table-body' in hx_target:
                    response_html = render_template('patient_table_body.html', patients=processed_patients)
                    # Add pagination headers for JavaScript to read
                    resp = make_response(response_html)
                    resp.headers['X-Current-Page'] = str(page)
                    resp.headers['X-Total-Pages'] = str(total_pages)
                    resp.headers['X-Total-Items'] = str(total)
                    resp.headers['X-Per-Page'] = str(per_page)
                    resp.headers['X-Has-Next'] = str(has_next).lower()
                    resp.headers['X-Has-Prev'] = str(has_prev).lower()
                    return resp
                else:
                    # For regular requests or HTMX requests targeting #content, return full page
                    logging.info(f"Returning full template with: page={page}, total_pages={total_pages}, total_items={total}, per_page={per_page}")
                    return render_template('patients.html', 
                                         patients=processed_patients,
                                         current_page=page,
                                         total_pages=total_pages,
                                         total_items=total,
                                         per_page=per_page,
                                         has_next=has_next,
                                         has_prev=has_prev)
            else:
                logging.error(f"FHIR request failed with status: {response.status_code}, response: {response.text}")
                return jsonify({"error": "Failed to fetch patients"}), 500
        except Exception as e:
            logging.error(f"Error in get_patients: {e}")
            return jsonify({"error": "Internal server error"}), 500

@app.route('/fhir/search_patients', methods=['POST'])
@login_required
def search_patients():   
    search_term = request.form.get('q', '').strip().lower()
    page = request.form.get('page', 1, type=int)
    per_page = request.form.get('per_page', 10, type=int)
    
    if not search_term:
        # If search is empty, return paginated patients
        return redirect(url_for('get_patients', page=page, per_page=per_page))
    
    # Search patients by name or identifier
    try:
        # For search, we need to fetch more records to filter client-side
        # This is not ideal but FHIR search capabilities may be limited
        response = fhir_get("/Patient?_count=1000", fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
        if response.status_code == 200:
            patients = response.json().get('entry', [])
            # Filter patients by name (case-insensitive, anywhere in given or family)
            filtered_patients = []
            for entry in patients:
                resource = entry.get('resource', {})
                names = resource.get('name', [])
                for name in names:
                    given_names = ' '.join(name.get('given', []))
                    family_name = name.get('family', '')
                    full_name = f"{given_names} {family_name}".strip().lower()
                    if search_term in full_name:
                        filtered_patients.append(entry)
                        break  # Only need to match one name per patient
            
            # Apply pagination to filtered results
            total_filtered = len(filtered_patients)
            skip = (page - 1) * per_page
            paginated_patients = filtered_patients[skip:skip + per_page]
            
            processed_patients = process_patient_results(paginated_patients)
            
            # Calculate pagination info for filtered results
            total_pages = (total_filtered + per_page - 1) // per_page
            has_next = page < total_pages
            has_prev = page > 1
            
            # Add pagination headers for JavaScript
            response_html = render_template('patient_table_body.html', patients=processed_patients)
            resp = make_response(response_html)
            resp.headers['X-Current-Page'] = str(page)
            resp.headers['X-Total-Pages'] = str(total_pages)
            resp.headers['X-Total-Items'] = str(total_filtered)
            resp.headers['X-Per-Page'] = str(per_page)
            resp.headers['X-Has-Next'] = str(has_next).lower()
            resp.headers['X-Has-Prev'] = str(has_prev).lower()
            return resp
        else:
            logging.error(f"API error: {response.status_code} when searching patients")
            return "<tr><td colspan='7'>Error searching patients</td></tr>", 500
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {str(e)}")
        return "<tr><td colspan='7'>Connection error, please try again</td></tr>", 500

@app.route('/fhir/Patient/<patient_id>')
@login_required
def get_patient(patient_id):
    print(f"get_patient called with patient_id: {patient_id}")
    response = fhir_get(f"/Patient/{patient_id}", fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
    session['current_patient_id'] = patient_id       
    print(f"FHIR response status code: {response.status_code}")
    if response.status_code == 200:
        patient = response.json()

        # Simplify work phone numbers
        work_telecoms = [telecom['value'] for telecom in patient.get('telecom', []) if telecom.get('use') == 'work']
        patient['work_phone'] = ', '.join(work_telecoms)

        # Simplify the address
        if patient.get('address'):
            address_parts = patient['address'][0].get('line', [])
            address_parts.extend([
                patient['address'][0].get('city', ''),
                patient['address'][0].get('state', ''),
                patient['address'][0].get('postalCode', '')
            ])
            patient['simple_address'] = ', '.join(filter(None, address_parts))  # Filter out empty strings

        # Simplify identifier, assume the first identifier is the most relevant
        if patient.get('identifier'):
            patient['simple_identifier'] = patient['identifier'][0].get('value', '')
            
        # Extract communication languages
        patient['languages'] = []
        if patient.get('communication'):
            for comm in patient['communication']:
                if 'language' in comm:
                    language_text = comm['language'].get('text', '')
                    if not language_text and 'coding' in comm['language']:
                        language_text = comm['language']['coding'][0].get('display', '')
                    if language_text:
                        preferred = 'Preferred' if comm.get('preferred', False) else ''
                        patient['languages'].append({'name': language_text, 'preferred': preferred})

        # Process age from birth date
        if patient.get('birthDate'):
            try:
                birth_date = datetime.strptime(patient['birthDate'], '%Y-%m-%d')
                today = datetime.now()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                patient['age'] = age
            except ValueError:
                patient['age'] = 'Unknown'

        return render_template('patient_details.html', patient=patient)
    else:
        print(f"Failed to fetch patient details. Status code: {response.status_code}, Response text: {response.text}")
        return jsonify({"error": "Failed to fetch patient details"}), 500


@app.route('/fhir/Patient/<patient_id>/summary', methods=['GET'])
def get_patient_summary(patient_id):
    response = fhir_get(
        f"/Patient/{patient_id}/$summary",
        fhir_server_url=get_fhir_server_url(),
        timeout=60
    )
    if response.status_code == 200:
        bundle = response.json()       
        bundle_json = json.dumps(bundle, indent=2)
        # Render the partial instead of returning raw JSON
        return render_template('partials/json_textarea.html', bundle_json=bundle_json)
    else:
        error_message = {"error": "Failed to fetch patient summary"}
        return render_template('partials/json_textarea.html', bundle_json=json.dumps(error_message, indent=2))
    

@app.route('/fhir/Procedures/<patient_id>')
@login_required
def get_procedures(patient_id):
    response = fhir_get(f"/Procedure?subject={patient_id}&_sort=-date&_count=5", fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
    if response.status_code == 200:
        procedures = response.json().get('entry', [])
        # Prepare procedures for rendering
        for proc in procedures:
            resource = proc['resource']
            performedDateTime = resource.get('performedDateTime', '')
            dt_performed = format_fhir_date(performedDateTime,"DT")
            resource['performedDate'] = dt_performed
            # Get name of procedure
            resource['procName'] = get_text_display(resource.get('code'))           
            # Get Reason for Procedure
            resource['procReason'] = get_text_display(resource.get('reasonCode', [{}])[0])
        return render_template('procedures.html', procedures=[proc['resource'] for proc in procedures])
    else:
        return "Procedures not found", 404

@app.route('/fhir/Immunisation/<patient_id>')
@login_required
def get_immunizations(patient_id):
    response = fhir_get(
        f"/Immunization?patient={patient_id}&_sort=-date&_count=10",
        fhir_server_url=get_fhir_server_url(),
        timeout=10
    )
    if response.status_code == 200:
        immunisations = response.json().get('entry', [])
        processed_immunisations = []
        for entry in immunisations:
            resource = entry.get('resource', {})
            # Vaccine display
            vaccine_display = get_text_display(resource.get('vaccineCode'))
            # Occurrence DateTime
            occurrence = resource.get('occurrenceDateTime', '')            
            dt_occurrence = format_fhir_date(occurrence)
            # Status
            status = resource.get('status', 'unknown')
            # Create vaccination summary
            processed_immunisations.append({
                'vaccine': vaccine_display,
                'date': dt_occurrence,
                'status': status
            })
        return render_template('immunisations.html', immunisations=processed_immunisations)
    else:
        return "Immunisation not found", 404

@app.route('/fhir/Requesters')
@login_required
def get_requesters():
    """
    Returns a list of PractitionerRoles with name, specialty, and PractitionerRole id for dropdown.
    Only includes PractitionerRoles with a known value in the specialty element.
    """
    response = fhir_get("/PractitionerRole?_include=PractitionerRole:practitioner&_count=100", fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
    if response.status_code != 200:
        return render_template('partials/requesters.html', requesters=[])

    bundle = response.json()
    entries = bundle.get('entry', [])
    practitioners = {}
    # Build a map of Practitioner id to name
    for entry in entries:
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'Practitioner':
            practitioner_id = resource.get('id')
            # Get full name
            name = resource.get('name', [{}])[0]
            full_name = ' '.join(name.get('given', [])) + ' ' + name.get('family', '')
            practitioners[practitioner_id] = full_name.strip()

    requesters = []
    for entry in entries:
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'PractitionerRole':
            role_id = resource.get('id')
            # Get practitioner name
            practitioner_ref = resource.get('practitioner', {}).get('reference', '')
            practitioner_id = practitioner_ref.split('/')[-1] if practitioner_ref else ''
            name = practitioners.get(practitioner_id, 'Unknown')
            # Get specialty display (first SNOMED if available)
            specialty_display = ''
            specialty_concepts = resource.get('specialty', [])
            if specialty_concepts and isinstance(specialty_concepts, list):
                for concept in specialty_concepts:
                    for coding in concept.get('coding', []):
                        if coding.get('system') == "http://snomed.info/sct" and coding.get('display'):
                            specialty_display = coding['display']
                            break
                    if specialty_display:
                        break
            # Only add requester if specialty_display is valued (not empty)
            if specialty_display:
                requester = {
                    "id": role_id,
                    "name": name,
                    "specialty": specialty_display
                }
                requesters.append(requester)

    # Sort by name
    requesters = sorted(requesters, key=lambda x: x["name"])
    return render_template('partials/requesters.html', requesters=requesters)
    

@app.route('/fhir/CopyToPractitioners')
@login_required
def get_copy_to_practitioners():
    """
    Returns a list of PractitionerRoles for the copyTo typeahead search.
    Supports filtering by name parameter.
    """
    # Get search query from request
    search_query = request.args.get('copyToPractitioner', '').strip().lower()
    
    response = fhir_get("/PractitionerRole?_include=PractitionerRole:practitioner&_count=100", fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
    if response.status_code != 200:
        return render_template('partials/copy_to_practitioners.html', practitioners=[])

    bundle = response.json()
    entries = bundle.get('entry', [])
    practitioners = {}
    # Build a map of Practitioner id to name
    for entry in entries:
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'Practitioner':
            practitioner_id = resource.get('id')
            # Get full name
            name = resource.get('name', [{}])[0]
            full_name = ' '.join(name.get('given', [])) + ' ' + name.get('family', '')
            practitioners[practitioner_id] = full_name.strip()

    all_practitioners = []
    for entry in entries:
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'PractitionerRole':
            role_id = resource.get('id')
            # Get practitioner name
            practitioner_ref = resource.get('practitioner', {}).get('reference', '')
            practitioner_id = practitioner_ref.split('/')[-1] if practitioner_ref else ''
            name = practitioners.get(practitioner_id, 'Unknown')
            # Get specialty display (first SNOMED if available)
            specialty_display = ''
            specialty_concepts = resource.get('specialty', [])
            if specialty_concepts and isinstance(specialty_concepts, list):
                for concept in specialty_concepts:
                    for coding in concept.get('coding', []):
                        if coding.get('system') == "http://snomed.info/sct" and coding.get('display'):
                            specialty_display = coding['display']
                            break
                    if specialty_display:
                        break
            # Only add practitioner if specialty_display is valued (not empty)
            if specialty_display:
                practitioner = {
                    "id": role_id,
                    "name": name,
                    "specialty": specialty_display
                }
                all_practitioners.append(practitioner)

    # Filter practitioners by search query if provided
    if search_query:
        filtered_practitioners = []
        for practitioner in all_practitioners:
            if (search_query in practitioner["name"].lower() or 
                search_query in practitioner["specialty"].lower()):
                filtered_practitioners.append(practitioner)
        all_practitioners = filtered_practitioners

    # Sort by name and limit to 10 results
    all_practitioners = sorted(all_practitioners, key=lambda x: x["name"])[:10]

    # Render a partial datalist for copyTo
    return render_template('partials/copy_to_practitioners.html', practitioners=all_practitioners)


@app.route('/fhir/Provider/<org_type>')
@login_required
def get_organisation_by_type(org_type):
    """
    Returns a dropdown list of Organisations matching the given type code.
    org_type: The SCT code for the organisation type (e.g., "310074003" for Pathology service provider)
    Uses SNOMED CT as the type system.
    """
    # Use SNOMED CT system for organisation type
    system = request.args.get('system', 'http://snomed.info/sct')
    # Search for organisations with the given type code and system
    search_url = f"/Organization?type={system}|{org_type}&_count=20"
    response = fhir_get(search_url, fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
    if response.status_code != 200:
        return render_template('partials/organisations.html', organisations=[])

    bundle = response.json()
    entries = bundle.get('entry', [])
    organisations = []
    # For testing SNP orders on pyro server
    snp_pathology = { "id": "05030000-ac10-0242-f1b3-08dde8e839a8", "name": "Sullivan Nicolaides Pathology" }    
    qxr_radiology = { "id": "05030000-ac10-0242-030b-08dde9b69fcf", "name": "Queensland X-Ray" } 
    organisations.append(snp_pathology)
    organisations.append(qxr_radiology)
    for entry in entries:
        resource = entry.get('resource', {})
        org_id = resource.get('id', '')
        name = resource.get('name', 'Unknown')
        organisations.append({
            "id": org_id,
            "name": name
        })

    # Render a partial dropdown list
    return render_template('partials/organisations.html', organisations=sorted(organisations,  key=lambda x: x["name"]))


@app.route('/fhir/LabResults/<patient_id>')
@login_required
def get_lab_results(patient_id):
    response = fhir_get(f"/Observation?patient={patient_id}&_sort=-date", fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)
    if response.status_code == 200:
        lab_results = response.json().get('entry', [])
        filtered_lab_results = []
        for result in lab_results:
            resource = result.get('resource', {})
            categories = resource.get('category', [])
            if not find_category(categories, "http://terminology.hl7.org/CodeSystem/observation-category", "laboratory"):
                continue  # Skip non-lab observations

            # Found a lab result
            unit = ""
            if 'valueQuantity' in resource:
                value = resource['valueQuantity'].get('value')
                unit = resource['valueQuantity'].get('unit', '')
            elif 'valueCodeableConcept' in resource:
                value = resource['valueCodeableConcept'].get('text')
                if not value and resource['valueCodeableConcept'].get('coding'):
                    value = resource['valueCodeableConcept']['coding'][0].get('display')
            else:
                value = resource.get('dataAbsentReason', {}).get('text', 'No result')
            resource['display_value'] = value
            resource['display_unit'] = unit

            test_display = get_text_display(resource.get('code'))
            resource['test_display'] = test_display 

            resource['formattedDate'] = format_fhir_date(resource.get('effectiveDateTime', 'DT'))
            filtered_lab_results.append(resource)

        return render_template('lab_results.html', lab_results=filtered_lab_results)
    else:
        return "Lab results not found", 404

@app.route('/fhir/VitalSigns/<patient_id>')
@login_required
def get_vital_signs(patient_id):
    # First, get blood pressure observations  85354-9 or 75367002
    bp_response = fhir_get(
        f"/Observation?patient={patient_id}&code=http://loinc.org|85354-9,http://snomed.info/sct|75367002&_sort=-date&_count=10", fhir_server_url=get_fhir_server_url(), timeout=10)
    
    # Get heart rate observations 8867-4 or http://snomed.info/sct|364075005
    hr_response = fhir_get(
        f"Observation?patient={patient_id}&code=http://loinc.org|8867-4,http://snomed.info/sct|364075005&_sort=-date&_count=10", fhir_server_url=get_fhir_server_url(), timeout=10) 
    
    # Get temperature observations. 8310-5 or 386725007
    temp_response = fhir_get(
        f"/Observation?patient={patient_id}&code=http://loinc.org|8310-5,http://snomed.info/sct|386725007&_sort=-date&_count=10", fhir_server_url=get_fhir_server_url(), timeout=10)
    
    # Get respiratory rate observations 9279-1 or 86290005
    resp_response = fhir_get(
        f"/Observation?patient={patient_id}&code=http://loinc.org|9279-1,http://snomed.info/sct|86290005&_sort=-date&_count=10", fhir_server_url=get_fhir_server_url(), timeout=10)

    vital_signs = []    
    # Process blood pressure readings
    if bp_response.status_code == 200:
        bp_data = bp_response.json().get('entry', [])
        for entry in bp_data:
            resource = entry.get('resource', {})
            
            # Extract the date
            effective_date = resource.get('effectiveDateTime', '')
            dt_observation = format_fhir_date(effective_date,"DT")
                
            # Extract components (systolic/diastolic)
            components = resource.get('component', [])
            systolic = None
            diastolic = None
            
            for component in components:
                coding = component.get('code', {}).get('coding', [{}])
                if coding and coding[0].get('display') == 'Systolic blood pressure':
                    systolic = component.get('valueQuantity', {}).get('value')
                elif coding and coding[0].get('display') == 'Diastolic blood pressure':
                    diastolic = component.get('valueQuantity', {}).get('value')
            
            # Only add if we have both systolic and diastolic
            if systolic is not None and diastolic is not None:
                vital_signs.append({
                    'date': dt_observation,
                    'type': 'Blood Pressure',
                    'value': f'{systolic}/{diastolic}',
                    'unit': 'mmHg',
                    'status': resource.get('status', 'unknown'),
                    'components': {
                        'systolic': systolic,
                        'diastolic': diastolic
                    }
                })
    
    # Process heart rate readings
    if hr_response.status_code == 200:
        hr_data = hr_response.json().get('entry', [])
        for entry in hr_data:
            resource = entry.get('resource', {})
            
            # Extract the date
            effective_date = resource.get('effectiveDateTime', '')
            dt_observation = format_fhir_date(effective_date,"DT")           
                
            # Get heart rate value
            value_quantity = resource.get('valueQuantity', {})
            value = value_quantity.get('value')
            
            # Make sure value is a number
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 0
            
            vital_signs.append({
                'date': dt_observation,
                'type': 'Heart Rate',
                'value': value,
                'unit': value_quantity.get('unit', 'bpm'),
                'status': resource.get('status', 'unknown')
            })
    
    # Process temperature readings
    if temp_response.status_code == 200:
        temp_data = temp_response.json().get('entry', [])
        for entry in temp_data:
            resource = entry.get('resource', {})
            
            # Extract the date
            effective_date = resource.get('effectiveDateTime', '')
            dt_observation = format_fhir_date(effective_date,"DT")
                
            # Get temperature value
            value_quantity = resource.get('valueQuantity', {})
            
            vital_signs.append({
                'date': dt_observation,
                'type': 'Temperature',
                'value': value_quantity.get('value', 'Unknown'),
                'unit': value_quantity.get('unit', '°C'),
                'status': resource.get('status', 'unknown')
            })
    
    # Process respiratory rate readings
    if resp_response.status_code == 200:
        resp_data = resp_response.json().get('entry', [])
        for entry in resp_data:
            resource = entry.get('resource', {})
            
            # Extract the date
            effective_date = resource.get('effectiveDateTime', '')
            dt_observation = format_fhir_date(effective_date,"DT")
                
            # Get respiratory rate value
            value_quantity = resource.get('valueQuantity', {})
            
            vital_signs.append({
                'date': dt_observation,
                'type': 'Respiratory Rate',
                'value': value_quantity.get('value', 'Unknown'),
                'unit': value_quantity.get('unit', '/min'),
                'status': resource.get('status', 'unknown')
            })
    
    # Sort vital signs by date (newest first)
    vital_signs.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('vital_signs.html', vital_signs=vital_signs)

@app.route('/fhir/Medications/<patient_id>')
@login_required
def get_medications(patient_id):
    # Get medications
    medications = []
    meds_response = fhir_get(f"/MedicationRequest?patient={patient_id}&_count=10", fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials(), timeout=10)       
    
    if meds_response.status_code == 200:
        meds_data = meds_response.json()
        # Check if 'entry' exists in the response
        if 'entry' in meds_data:
            for entry in meds_data.get('entry', []):
                resource = entry.get('resource', {})
                
                # Extract the date
                authored_date = resource.get('authoredOn', '')
                dt_authored = format_fhir_date(authored_date)
                
                # Extract medication reference or codeable concept
                medication_name = "Unknown Medication"
                if resource.get('medicationReference'):
                    medication_name = resource['medicationReference'].get('display', 'Unknown Medication')
                elif resource.get('medicationCodeableConcept'):
                    medication_name = get_text_display(resource['medicationCodeableConcept'], default="Unknown Medication")
                                
                                # Get dosage instructions
                dosage_instructions = []
                if resource.get('dosageInstruction'):
                    for dosage in resource['dosageInstruction']:
                        text = dosage.get('text', '')
                        if text:
                            dosage_instructions.append(text)
                
                # Get status
                status = resource.get('status', 'unknown')
                
                medications.append({
                    'date': dt_authored,
                    'name': medication_name,
                    'dosage': ', '.join(dosage_instructions) if dosage_instructions else 'No specific instructions',
                    'status': status
                })
        
        # Log if no medications found
        if not medications:
            logging.info(f"No medications found for patient {patient_id}")
    
    # Sort medications by date (newest first)
    medications.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('medications.html', medications=medications)

@app.route('/fhir/Allergies/<patient_id>')
@login_required
def get_allergies(patient_id):
    # Get allergies
    allergy_response = fhir_get(
        f"/AllergyIntolerance?patient={patient_id}&_count=10", get_fhir_server_url(), timeout=10)      
    allergies = []    
    if allergy_response.status_code == 200:
        allergy_data = allergy_response.json()
        # Check if 'entry' exists in the response
        if 'entry' in allergy_data:
            for entry in allergy_data.get('entry', []):
                resource = entry.get('resource', {})
                
                # Extract the date
                recorded_date = resource.get('recordedDate', '')
                dt_recorded = format_fhir_date(recorded_date)               
                
                # Extract allergy code or display
                allergy_name = get_text_display(resource.get('code'))                
                
                # Get reaction
                reactions = []
                if resource.get('reaction'):
                    for reaction in resource['reaction']:
                        if reaction.get('manifestation'):
                            for manifestation in reaction['manifestation']:
                                reactions.append(get_text_display(manifestation))                
                # Get status
                clinical_status = "Unknown"
                if resource.get('clinicalStatus'):
                    if resource['clinicalStatus'].get('coding'):
                        clinical_status = resource['clinicalStatus']['coding'][0].get('display', 'Unknown')
                    else:
                        clinical_status = resource['clinicalStatus'].get('text', 'Unknown')
                
                # Get severity
                severity = resource.get('severity', 'unknown')
                
                allergies.append({
                    'date': dt_recorded,
                    'name': allergy_name,
                    'reactions': reactions,
                    'severity': severity,
                    'status': clinical_status
                })
        
        # Log if no allergies found
        if not allergies:
            logging.info(f"No allergies found for patient {patient_id}")
    
    # Sort allergies by date (newest first)
    allergies.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('allergies.html', allergies=allergies)


@app.route('/fhir/diagnosticrequest/bundler/<patient_id>', methods=['POST'])
def create_diagnostic_request_bundle(patient_id):
    form_data = get_form_data(request)
    form_data['patient_id'] = patient_id
    # Log the processed form data in a readable format
    logging.info(f"Form data: {json.dumps(form_data, indent=2)}")

    #with open('./json/service_request_bundle.json', 'r', encoding='utf-8') as f:
    #    bundle = json.load(f)
    bundle = create_request_bundle(form_data=form_data, fhir_server_url=get_fhir_server_url(), auth_credentials=get_fhir_auth_credentials())
    bundle_json = json.dumps(bundle, indent=2)
    return render_template('partials/json_textarea.html', bundle_json=bundle_json), 200


@app.route('/fhir/diagvalueset/expand')
def diag_valueset_expand():
    """
    Expands a ValueSet for Pathology or Radiology test names using a terminology server.
    Query params:
      - type: 'Pathology' or 'Radiology'
      - q: search string
    """
    request_cat = request.args.get('requestCategory', '').lower()
    query = request.args.get('testName', '').strip()
    ###logging.info(f'Request Category:[{request_cat}] should be one of pathology, radiology')
    ###logging.info(f'testName:[{query}]')
    if not request_cat or not query or request_cat not in ['pathology', 'radiology']:
        return render_template('partials/test_names.html', testNames=[])
    # Map test type to ValueSet URL (update these URLs to match your terminology server)
    valueset_map = {
        'pathology': 'http://pathologyrequest.example.com.au/ValueSet/boosted',   #  SNOMED Pathology Test ValueSet
        'radiology': 'http://radiologyrequest.example.com.au/ValueSet/boosted',   #  SNOMED Radiology Test ValueSet
    }
    valueset_url = valueset_map[request_cat]

    terminology_server = "https://r4.ontoserver.csiro.au/fhir" 
    expand_url = f"{terminology_server}/ValueSet/$expand"
    params = {
        "url": valueset_url,
        "filter": query,
        "count": 15
    }

    try:
        logging.info(f'Request URL: {expand_url}?url={params.get("url")}&filter={params.get("filter")}&count={params.get("count")}')
        resp = requests.get(expand_url, params=params, timeout=10)
        logging.info(f'Response status: {resp.status_code}')
        resp.raise_for_status()
        data = resp.json()
        logging.info(f'Response data keys: {list(data.keys())}')
        testNames = []
        contains = data.get("expansion", {}).get("contains", [])
        logging.info(f'Found {len(contains)} test names for query "{query}"')
        for item in contains:
            code = item.get("code", "")
            display = item.get("display") or code
            if display:
                testNames.append({
                    "code": code,
                    "display": display
                })
        return render_template('partials/test_names.html', testNames=testNames)
    except requests.exceptions.RequestException as e:
        logging.error(f'Request error in diag_valueset_expand: {str(e)}')
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f'Response status: {e.response.status_code}')
            logging.error(f'Response text: {e.response.text}')
        return render_template('partials/test_names.html', testNames=[])
    except Exception as e:
        logging.error(f'General error in diag_valueset_expand: {str(e)}')
        logging.error(f'Error type: {type(e).__name__}')
        return render_template('partials/test_names.html', testNames=[])

@app.route('/fhir/reasonvalueset/expand')
def reason_valueset_expand():
    """
    Expands a ValueSet for the Reason for Requesting Pathology or Radiology tests using a terminology server.
    Query params:
      - q: search string
    """
    query = request.args.get('reason', '').strip()

    terminology_server = "https://r4.ontoserver.csiro.au/fhir" 
    expand_url = f"{terminology_server}/ValueSet/$expand"
    vs = "https://healthterminologies.gov.au/fhir/ValueSet/reason-for-request-1"
    params = {
        "url": vs,
        "filter": query,
        "count": 10
    }
    try:
        ###logging.info(f'{expand_url}?url={params.get("url")}&filter={params.get("filter")}&count={params.get("count")}')
        resp = requests.get(expand_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        ###logging.info(data)
        reasons = []
        contains = data.get("expansion", {}).get("contains", [])
        for item in contains:
            code = item.get("code", "")
            display = item.get("display") or code
            if display:
                reasons.append({
                    "code": code,
                    "display": display
                })
        return render_template('partials/reasons.html', reasons=reasons)
    except Exception as e:
        print(e.with_traceback)
        return render_template('partials/reasons.html', reasons=[])


@app.route('/fhir/specimentype/expand')
def specimen_type_expand():
    """
    Expands the AU Specimen Type ValueSet for specimen type selection.
    Query params:
      - specimenType: search string
    """
    query = request.args.get('specimenType', '').strip()
    if not query:
        return '<option value="">Start typing to search specimen types...</option>'
    
    valueset_url = 'https://healthterminologies.gov.au/fhir/ValueSet/specimen-type-1'
    terminology_server = "https://r4.ontoserver.csiro.au/fhir" 
    expand_url = f"{terminology_server}/ValueSet/$expand"
    params = {
        "url": valueset_url,
        "filter": query,
        "count": 15
    }

    try:
        resp = requests.get(expand_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        options = []
        contains = data.get("expansion", {}).get("contains", [])
        for item in contains:
            code = item.get("code", "")
            display = item.get("display") or code
            if display:
                options.append(f'<option value="{display}" data-code="{code}">{display}</option>')
        
        return ''.join(options)
    except Exception as e:
        print(f"Error expanding specimen type ValueSet: {e}")
        return '<option value="">Error loading specimen types</option>'


@app.route('/fhir/collectionmethod/expand')
def collection_method_expand():
    """
    Expands the AU Specimen Collection Procedure ValueSet for collection method selection.
    Query params:
      - collectionMethod: search string
    """
    query = request.args.get('collectionMethod', '').strip()
    if not query:
        return '<option value="">Start typing to search collection methods...</option>'
    
    valueset_url = 'https://healthterminologies.gov.au/fhir/ValueSet/specimen-collection-procedure-1'
    terminology_server = "https://r4.ontoserver.csiro.au/fhir" 
    expand_url = f"{terminology_server}/ValueSet/$expand"
    params = {
        "url": valueset_url,
        "filter": query,
        "count": 15
    }

    try:
        resp = requests.get(expand_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        options = []
        contains = data.get("expansion", {}).get("contains", [])
        for item in contains:
            code = item.get("code", "")
            display = item.get("display") or code
            if display:
                options.append(f'<option value="{display}" data-code="{code}">{display}</option>')
        
        return ''.join(options)
    except Exception as e:
        print(f"Error expanding collection method ValueSet: {e}")
        return '<option value="">Error loading collection methods</option>'


@app.route('/fhir/bodysite/expand')
def body_site_expand():
    """
    Expands the AU Body Site ValueSet for body site selection.
    Query params:
      - bodySite: search string
    """
    query = request.args.get('bodySite', '').strip()
    if not query:
        return '<option value="">Start typing to search body sites...</option>'
    
    valueset_url = 'https://healthterminologies.gov.au/fhir/ValueSet/body-site-1'
    terminology_server = "https://r4.ontoserver.csiro.au/fhir" 
    expand_url = f"{terminology_server}/ValueSet/$expand"
    params = {
        "url": valueset_url,
        "filter": query,
        "count": 15
    }

    try:
        resp = requests.get(expand_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        options = []
        contains = data.get("expansion", {}).get("contains", [])
        for item in contains:
            code = item.get("code", "")
            display = item.get("display") or code
            if display:
                options.append(f'<option value="{display}" data-code="{code}">{display}</option>')
        
        return ''.join(options)
    except Exception as e:
        print(f"Error expanding body site ValueSet: {e}")
        return '<option value="">Error loading body sites</option>'


@app.route('/fhir/Demographics')
@login_required
def get_demographics():
    """Get patient demographics statistics for visualization"""
    # Fetch patients for demographic analysis
    response = fhir_get(
        f"/Patient?_count=100", fhir_server_url=get_fhir_server_url(), timeout=10)  
    
    if response.status_code == 200:
        patients = response.json().get('entry', [])
        
        # Initialize counters
        gender_counts = {"male": 0, "female": 0, "other": 0, "unknown": 0}
        age_groups = {"0-18": 0, "19-35": 0, "36-55": 0, "56-75": 0, "76+": 0, "unknown": 0}
        
        current_year = datetime.now().year
        
        # Process each patient
        for patient_entry in patients:
            resource = patient_entry.get('resource', {})
            
            # Count genders
            gender = resource.get('gender', '').lower()
            if gender in gender_counts:
                gender_counts[gender] += 1
            else:
                gender_counts["unknown"] += 1
                
            # Determine age group
            birth_date = resource.get('birthDate')
            if birth_date and len(birth_date) >= 4:
                try:
                    birth_year = int(birth_date[:4])
                    age = current_year - birth_year
                    
                    if age <= 18:
                        age_groups["0-18"] += 1
                    elif age <= 35:
                        age_groups["19-35"] += 1
                    elif age <= 55: 
                        age_groups["36-55"] += 1
                    elif age <= 75:
                        age_groups["56-75"] += 1
                    else:
                        age_groups["76+"] += 1
                except ValueError:
                    age_groups["unknown"] += 1
            else:
                age_groups["unknown"] += 1
        
        # Calculate total for percentages
        total_patients = sum(gender_counts.values())
        
        demographics = {
            "gender_counts": gender_counts,
            "age_groups": age_groups,
            "total_patients": total_patients
        }
        
        # Add ServiceRequest and Observation statistics
        service_request_stats = {}
        observation_stats = {}
        
        # Fetch ServiceRequests with details
        service_request_response = fhir_get(
            f"/ServiceRequest?_count=1000", fhir_server_url=get_fhir_server_url(), timeout=15)
        
        # Fetch Observations with details  
        observation_response = fhir_get(
            f"/Observation?_count=1000", fhir_server_url=get_fhir_server_url(), timeout=15)
        
        # Process ServiceRequests
        service_requests = []
        if service_request_response.status_code == 200:
            sr_data = service_request_response.json()
            service_requests = sr_data.get('entry', [])
            
            for entry in service_requests:
                resource = entry.get('resource', {})
                status = resource.get('status', 'unknown')
                
                # Get code.text
                code = resource.get('code', {})
                code_text = code.get('text', 'No description')
                if not code_text or code_text == 'No description':
                    if code.get('coding'):
                        code_text = code['coding'][0].get('display', 'No description')
                
                # Get category info
                category = resource.get('category', [])
                category_text = 'No category'
                if category and len(category) > 0:
                    cat = category[0]
                    category_text = cat.get('text', '')
                    if not category_text and cat.get('coding'):
                        category_text = cat['coding'][0].get('display', 'No category')
                
                # Create key for grouping
                key = (code_text, status, category_text)
                service_request_stats[key] = service_request_stats.get(key, 0) + 1
        
        # Process Observations
        observations = []
        if observation_response.status_code == 200:
            obs_data = observation_response.json()
            observations = obs_data.get('entry', [])
            
            for entry in observations:
                resource = entry.get('resource', {})
                status = resource.get('status', 'unknown')
                
                # Get code.text
                code = resource.get('code', {})
                code_text = code.get('text', 'No description')
                if not code_text or code_text == 'No description':
                    if code.get('coding'):
                        code_text = code['coding'][0].get('display', 'No description')
                
                # Get category info
                category = resource.get('category', [])
                category_text = 'No category'
                if category and len(category) > 0:
                    cat = category[0]
                    category_text = cat.get('text', '')
                    if not category_text and cat.get('coding'):
                        category_text = cat['coding'][0].get('display', 'No category')
                
                # Create key for grouping
                key = (code_text, status, category_text)
                observation_stats[key] = observation_stats.get(key, 0) + 1
        
        # Convert to sorted lists for template (sort by count descending)
        sr_stats_list = []
        for (code_text, status, category_text), count in sorted(service_request_stats.items(), key=lambda x: x[1], reverse=True):
            sr_stats_list.append({
                'code_text': code_text,
                'status': status,
                'category_text': category_text,
                'count': count
            })
        
        obs_stats_list = []
        for (code_text, status, category_text), count in sorted(observation_stats.items(), key=lambda x: x[1], reverse=True):
            obs_stats_list.append({
                'code_text': code_text, 
                'status': status,
                'category_text': category_text,
                'count': count
            })
        
        return render_template('demographics.html', 
                             demographics=demographics,
                             service_request_stats=sr_stats_list,
                             observation_stats=obs_stats_list,
                             sr_total=len(service_requests),
                             obs_total=len(observations))
    else:
        return jsonify({"error": "Failed to fetch patient demographics"}), 500

@app.route('/fhir/Dashboard')
@login_required
def get_dashboard():
    """Get dashboard data for the main dashboard view"""
    # Fetch patients
    patient_response = fhir_get(
        f"/Patient?_count=100", fhir_server_url=get_fhir_server_url(), timeout=10)  
    
    # Fetch observations count
    observation_response = fhir_get(
        f"/Observation?_summary=count", fhir_server_url=get_fhir_server_url(), timeout=10)  
    
    # Fetch group tasks with tag filter
    group_tasks_response = fhir_get(
        f"/Task?_tag=http://terminology.hl7.org.au/CodeSystem/resource-tag|fulfilment-task-group", 
        fhir_server_url=get_fhir_server_url(), timeout=10)
    
    # Fetch ServiceRequests count
    service_requests_response = fhir_get(
        f"/ServiceRequest?_summary=count", fhir_server_url=get_fhir_server_url(), timeout=10)
    
    patient_count = 0
    observation_count = 0
    service_request_count = 0
    gender_counts = {"male": 0, "female": 0, "other": 0, "unknown": 0}
    group_task_status_counts = {}
    group_task_business_status_counts = {}
    recent_patients = []
    
    if patient_response.status_code == 200:
        patient_data = patient_response.json()
        patients = patient_data.get('entry', [])
        patient_count = len(patients)     
                
        # Get recent patients and count genders
        recent_patients_data = patients[:5]  # Just take the first 5 for simplicity
        recent_patients = process_patient_results(recent_patients_data)
        
        # Count genders for all patients
        for patient_entry in patients:
            resource = patient_entry.get('resource', {})
            gender = resource.get('gender', '').lower()
            if gender in gender_counts:
                gender_counts[gender] += 1
            else:
                gender_counts["unknown"] += 1
    
    if observation_response.status_code == 200:
        observation_data = observation_response.json()
        observation_count = observation_data.get('total', 0)
    
    if service_requests_response.status_code == 200:
        service_request_data = service_requests_response.json()
        service_request_count = service_request_data.get('total', 0)
    
    # Process group tasks counts by status and businessStatus
    if group_tasks_response.status_code == 200:
        group_tasks_data = group_tasks_response.json()
        group_tasks = group_tasks_data.get('entry', [])
        
        for task_entry in group_tasks:
            task_resource = task_entry.get('resource', {})
            
            # Count by status
            status = task_resource.get('status', 'unknown')
            group_task_status_counts[status] = group_task_status_counts.get(status, 0) + 1
            
            # Count by businessStatus
            business_status = task_resource.get('businessStatus', {})
            if business_status:
                # Get text or first coding display
                business_status_text = business_status.get('text', '')
                if not business_status_text and business_status.get('coding'):
                    business_status_text = business_status['coding'][0].get('display', 'unknown')
                if not business_status_text:
                    business_status_text = 'unknown'
            else:
                business_status_text = 'no-business-status'
            
            group_task_business_status_counts[business_status_text] = group_task_business_status_counts.get(business_status_text, 0) + 1

    dashboard_data = {
        'patient_count': patient_count,
        'observation_count': observation_count,
        'service_request_count': service_request_count,
        'gender_counts': gender_counts,
        'group_task_status_counts': group_task_status_counts,
        'group_task_business_status_counts': group_task_business_status_counts,
        'recent_patients': recent_patients,
        'fhir_server_url': get_fhir_server_url()
    }
    
    return render_template('dashboard.html', **dashboard_data)


@app.route('/logout')
@login_required # Ensure user is logged in to log out
def logout():
    logout_user()
    logging.info("User logged out.")
    return redirect(url_for('index'))

@app.route('/login')
def login():
    # Show dedicated login page for unauthenticated users
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/basic_auth_login', methods=['POST'])
def basic_auth_login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        # Try to extract from header manually (for fetch API)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Basic '):
            import base64
            try:
                decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = decoded.split(':', 1)
            except Exception:
                return jsonify({'success': False, 'error': 'Invalid auth header'}), 401
        else:
            return jsonify({'success': False, 'error': 'Missing credentials'}), 401
    else:
        username = auth.username
        password = auth.password

    # Replace this with your real user/password check
    if username == 'testuser' and password == 'testpass':
        user = User(id=username)
        login_user(user)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid login code or password'}), 401

@app.route('/fhir/Stats')
@login_required
def get_stats():
    """Get statistics page showing ServiceRequest and Observation summaries"""
    
    # Fetch ServiceRequests with details
    service_request_response = fhir_get(
        f"/ServiceRequest?_count=1000", fhir_server_url=get_fhir_server_url(), timeout=15)
    
    # Fetch Observations with details  
    observation_response = fhir_get(
        f"/Observation?_count=1000", fhir_server_url=get_fhir_server_url(), timeout=15)
    
    service_request_stats = {}
    observation_stats = {}
    
    # Process ServiceRequests
    if service_request_response.status_code == 200:
        sr_data = service_request_response.json()
        service_requests = sr_data.get('entry', [])
        
        for entry in service_requests:
            resource = entry.get('resource', {})
            status = resource.get('status', 'unknown')
            
            # Get code.text
            code = resource.get('code', {})
            code_text = code.get('text', 'No description')
            if not code_text or code_text == 'No description':
                if code.get('coding'):
                    code_text = code['coding'][0].get('display', 'No description')
            
            # Get category info
            category = resource.get('category', [])
            category_text = 'No category'
            if category and len(category) > 0:
                cat = category[0]
                category_text = cat.get('text', '')
                if not category_text and cat.get('coding'):
                    category_text = cat['coding'][0].get('display', 'No category')
            
            # Create key for grouping
            key = (code_text, status, category_text)
            service_request_stats[key] = service_request_stats.get(key, 0) + 1
    
    # Process Observations
    if observation_response.status_code == 200:
        obs_data = observation_response.json()
        observations = obs_data.get('entry', [])
        
        for entry in observations:
            resource = entry.get('resource', {})
            status = resource.get('status', 'unknown')
            
            # Get code.text
            code = resource.get('code', {})
            code_text = code.get('text', 'No description')
            if not code_text or code_text == 'No description':
                if code.get('coding'):
                    code_text = code['coding'][0].get('display', 'No description')
            
            # Get category info
            category = resource.get('category', [])
            category_text = 'No category'
            if category and len(category) > 0:
                cat = category[0]
                category_text = cat.get('text', '')
                if not category_text and cat.get('coding'):
                    category_text = cat['coding'][0].get('display', 'No category')
            
            # Create key for grouping
            key = (code_text, status, category_text)
            observation_stats[key] = observation_stats.get(key, 0) + 1
    
    # Convert to sorted lists for template
    sr_stats_list = []
    for (code_text, status, category_text), count in sorted(service_request_stats.items()):
        sr_stats_list.append({
            'code_text': code_text,
            'status': status,
            'category_text': category_text,
            'count': count
        })
    
    obs_stats_list = []
    for (code_text, status, category_text), count in sorted(observation_stats.items()):
        obs_stats_list.append({
            'code_text': code_text, 
            'status': status,
            'category_text': category_text,
            'count': count
        })
    
    stats_data = {
        'service_request_stats': sr_stats_list,
        'observation_stats': obs_stats_list,
        'sr_total': len(service_requests) if service_request_response.status_code == 200 else 0,
        'obs_total': len(observations) if observation_response.status_code == 200 else 0,
        'fhir_server_url': get_fhir_server_url()
    }
    
    return render_template('stats.html', **stats_data)

if __name__ == '__main__' and os.environ.get('TESTING') != 'true':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5001))
    # Bind to all interfaces to ensure localhost works on macOS
    app.run(host='0.0.0.0', port=port, debug=debug_mode)