# fhir-htmx-app
 A simplified app to showcase HTMX & FHIR integration. 

# FHIR Patient Dashboard

This Flask application provides a simple yet effective dashboard for viewing patient data fetched from the FHIR API using the HAPI test server. It leverages HTMX 2 and Bootstrap 5 for a responsive and dynamic user experience without full page reloads.

## Features

- **Dynamic Patient Listing**: View a list of patients dynamically loaded from the FHIR server.
- **Patient Details View**: Click on a patient to view detailed information including demographics, contact info, and identifiers.
- **Lab Results**: View recent lab results for each patient, formatted and displayed interactively.

## Technologies Used

- **Flask**: A lightweight WSGI web application framework.
- **HTMX**: Allows modern AJAX and CSS transitions making the frontend dynamic and interactive.
- **Bootstrap 5**: For styling and responsive design.

## Setup and Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/your-repository/fhir-patient-dashboard.git
   cd fhir-patient-dashboard
   ```

2. **Setup a Virtual Environment (optional but recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Requirements**

   ```bash
   pip install flask requests
   ```

4. **Run the Application**

   ```bash
   python app.py
   ```

   This will start the server on `http://127.0.0.1:5000/` where you can access the dashboard.

## Usage

- Navigate to `http://127.0.0.1:5000/` in your browser to see the list of patients.
- Click on any patient to view more detailed information and their recent lab results.

## Contributing

Contributions to the FHIR Patient Dashboard are welcome!

1. **Fork the Repository**
2. **Create your Feature Branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit your Changes** (`git commit -m 'Add some AmazingFeature'`)
4. **Push to the Branch** (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

daveymason.com
Project Link: [https://github.com/daveymason/fhir-patient-dashboard](https://github.com/daveymason/fhir-patient-dashboard)

Feel free to contact for more information or any issues related to the project.

## Acknowledgements
Logo is an icon by Freepik [from Flaticon](https://www.freepik.com/icon/computer_8811410#fromView=search&page=1&position=5&uuid=7f2f0cf5-731f-4ab9-9ab6-1ec888c8328b).
```