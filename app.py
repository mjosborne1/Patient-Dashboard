from flask import Flask, render_template, jsonify
import requests
import logging
from datetime import datetime

app = Flask(__name__)
FHIR_SERVER = 'http://hapi.fhir.org/baseR4'

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fhir/Patients')
def get_patients():
    response = requests.get(f"{FHIR_SERVER}/Patient?_count=10")
    if response.status_code == 200:
        patients = response.json().get('entry', [])
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

        return render_template('patients.html', patients=processed_patients)
    else:
        return jsonify({"error": "Failed to fetch patients"}), 500

@app.route('/fhir/Patient/<patient_id>')
def get_patient(patient_id):
    response = requests.get(f"{FHIR_SERVER}/Patient/{patient_id}")
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

        return render_template('patient_details.html', patient=patient)
    else:
        return jsonify({"error": "Failed to fetch patient details"}), 500

@app.route('/fhir/LabResults/<patient_id>')
def get_lab_results(patient_id):
    response = requests.get(f"{FHIR_SERVER}/Observation?patient={patient_id}&_sort=-date&_count=5")
    if response.status_code == 200:
        lab_results = response.json().get('entry', [])
        # Prepare lab results for rendering
        for result in lab_results:
            effectiveDateTime = result['resource'].get('effectiveDateTime', '')
            formatted_date = datetime.strptime(effectiveDateTime[:-6], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
            result['resource']['formattedDate'] = formatted_date
        # Render the results into HTML using the lab_results template
        return render_template('lab_results.html', lab_results=lab_results)
    else:
        return "Lab results not found", 404

if __name__ == '__main__':
    app.run(debug=True)