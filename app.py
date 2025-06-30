from flask import Flask, g, render_template, jsonify, request, session, redirect, url_for
import requests
import logging
from flask_login import LoginManager, AnonymousUserMixin, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
import os  # Add os module for environment variables
from fhirpathpy import evaluate
from fhirutils import fhir_get, format_fhir_date


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
    # Prefer user-supplied, fallback to default
    url = request.json.get('fhir_server_url') if request.is_json and request.json is not None else None
    if not url:
        url = os.environ.get('FHIR_SERVER_URL', 'https://smile.sparked-fhir.com/aucore/fhir/DEFAULT')
    return url

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
    response = fhir_get("/Patient?_count=10", fhir_server_url=get_fhir_server_url(), timeout=10)
    if response.status_code == 200:
        patients = response.json().get('entry', [])
        processed_patients = process_patient_results(patients)
        return render_template('patient_table_body.html', patients=processed_patients)
    else:
        return "<tr><td colspan='7'>Error loading patients</td></tr>", 500

@app.route('/fhir/Patients')
@login_required
def get_patients():
    response = fhir_get("/Patient?_count=10", fhir_server_url=get_fhir_server_url(), timeout=10)
    if response.status_code == 200:
        patients = response.json().get('entry', [])
        processed_patients = process_patient_results(patients)
        return render_template('patients.html', patients=processed_patients)
    else:
        return jsonify({"error": "Failed to fetch patients"}), 500

@app.route('/fhir/search_patients', methods=['POST'])
@login_required
def search_patients():   
    search_term = request.form.get('q', '').strip().lower()
    
    if not search_term:
        # If search is empty, return all patients
        return get_patients_table_body()
    
    # Search patients by name or identifier
    try:
        # Fetch a bundle of patients (increase _count as needed)
        response = fhir_get("/Patient?_count=1000", fhir_server_url=get_fhir_server_url(), timeout=10)
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
            processed_patients = process_patient_results(filtered_patients)
            return render_template('patient_table_body.html', patients=processed_patients)
        else:
            logging.error(f"API error: {response.status_code} when searching patients")
            return "<tr><td colspan='7'>Error searching patients</td></tr>", 500
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {str(e)}")
        return "<tr><td colspan='7'>Connection error, please try again</td></tr>", 500

@app.route('/fhir/Patient/<patient_id>')
@login_required
def get_patient(patient_id):
    response = fhir_get(f"/Patient/{patient_id}", fhir_server_url=get_fhir_server_url(), timeout=10)       
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
        return jsonify({"error": "Failed to fetch patient details"}), 500

@app.route('/fhir/Procedures/<patient_id>')
@login_required
def get_procedures(patient_id):
    response = fhir_get(f"/Procedure?subject={patient_id}&_sort=-date&_count=5", fhir_server_url=get_fhir_server_url(), timeout=10)
    if response.status_code == 200:
        procedures = response.json().get('entry', [])
        # Prepare procedures for rendering
        for proc in procedures:
            resource = proc['resource']
            performedDateTime = resource.get('performedDateTime', '')
            if performedDateTime:
                try:
                    if 'T' in performedDateTime:
                        formatted_date = datetime.strptime(performedDateTime[:19], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
                    else:
                        formatted_date = datetime.strptime(performedDateTime, '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    formatted_date = performedDateTime
                resource['performedDate'] = formatted_date
            else:
                resource['performedDate'] = ''
            # Get name of procedure
            resource['procName'] = 'Unknown'
            code = resource.get('code', {})
            codings = code.get('coding', [])
            for coding in codings:
                if coding.get('system') == "http://snomed.info/sct":
                    if coding.get('display'):
                        resource['procName'] = coding.get('display')
                    else:
                        resource['procName'] = code.get('text', 'Unknown')
            # Get Reason for Procedure
            resource['procReason'] = 'Unknown'
            for reason in resource.get('reasonCode', []):
                codings = reason.get('coding', [])
                for coding in codings:
                    if coding.get('display'):
                        resource['procReason'] = coding.get('display')
                    else:
                        resource['procReason'] = reason.get('text', 'Unknown')
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
            vaccine_display = "Unknown"
            vaccine_code = resource.get('vaccineCode', {})
            codings = vaccine_code.get('coding', [])
            # Try to get display from coding, else fallback to text
            if codings and codings[0].get('display'):
                vaccine_display = codings[0]['display']
            elif vaccine_code.get('text'):
                vaccine_display = vaccine_code['text']
            else:
                vaccine_display = "Unknown"
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

@app.route('/fhir/LabResults/<patient_id>')
@login_required
def get_lab_results(patient_id):
    response = fhir_get(f"/Observation?patient={patient_id}&_sort=-date&_count=5", fhir_server_url=get_fhir_server_url(), timeout=10)
    if response.status_code == 200:
        lab_results = response.json().get('entry', [])
         # Filter for laboratory category in Python
        filtered_lab_results = []
        for result in lab_results:
            resource = result.get('resource', {})
            categories = resource.get('category', [])
            for cat in categories:
                codings = cat.get('coding', [])
                for coding in codings:
                    if (
                        coding.get('system') == "http://terminology.hl7.org/CodeSystem/observation-category"
                        and coding.get('code') == "laboratory"
                    ):
                        filtered_lab_results.append(result)
                        break  # Found laboratory, no need to check further
                else:
                    continue
                break  # Break outer loop if found
        # Prepare lab results for rendering
        for result in filtered_lab_results:
            effectiveDateTime = result['resource'].get('performedDateTime', '')
            dt_observation = format_fhir_date(effectiveDateTime)
            result['resource']['formattedDate'] = dt_observation 
        # Render the results into HTML using the lab_results template
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
            dt_observation = format_fhir_date(effective_date)
                
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
            dt_observation = format_fhir_date(effective_date)           
                
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
            dt_observation = format_fhir_date(effective_date)
                
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
            dt_observation = format_fhir_date(effective_date)
                
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
    meds_response = fhir_get(f"/MedicationRequest?patient={patient_id}&_count=10", fhir_server_url=get_fhir_server_url(), timeout=10)       
    
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
                    coding = resource['medicationCodeableConcept'].get('coding', [{}])
                    if coding:
                        medication_name = coding[0].get('display', 'Unknown Medication')
                    else:
                        medication_name = resource['medicationCodeableConcept'].get('text', 'Unknown Medication')
                
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
                allergy_name = "Unknown Allergen"
                if resource.get('code'):
                    coding = resource['code'].get('coding', [{}])
                    if coding:
                        allergy_name = coding[0].get('display', 'Unknown Allergen')
                    else:
                        allergy_name = resource['code'].get('text', 'Unknown Allergen')
                
                # Get reaction
                reactions = []
                if resource.get('reaction'):
                    for reaction in resource['reaction']:
                        if reaction.get('manifestation'):
                            for manifestation in reaction['manifestation']:
                                if manifestation.get('coding'):
                                    reactions.append(manifestation['coding'][0].get('display', ''))
                                elif manifestation.get('text'):
                                    reactions.append(manifestation['text'])
                
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
        
        return render_template('demographics.html', demographics=demographics)
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
    
    patient_count = 0
    observation_count = 0
    gender_counts = {"male": 0, "female": 0, "other": 0, "unknown": 0}
    recent_patients = []
    
    if patient_response.status_code == 200:
        patient_data = patient_response.json()
        patients = patient_data.get('entry', [])
        patient_count = len(patients)
        
        # Process gender counts
        for patient_entry in patients:
            resource = patient_entry.get('resource', {})
            
            # Count genders
            gender = resource.get('gender', '').lower()
            if gender in gender_counts:
                gender_counts[gender] += 1
            else:
                gender_counts["unknown"] += 1
                
        # Get recent patients
        recent_patients_data = patients[:5]  # Just take the first 5 for simplicity
        recent_patients = process_patient_results(recent_patients_data)
    
    if observation_response.status_code == 200:
        observation_data = observation_response.json()
        observation_count = observation_data.get('total', 0)
    
    dashboard_data = {
        'patient_count': patient_count,
        'observation_count': observation_count,
        'gender_counts': gender_counts,
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

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode)