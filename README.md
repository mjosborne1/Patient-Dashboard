# 🏥 FHIR Patient Dashboard

A modern Flask app for exploring patient data from a FHIR API, using [HTMX](https://htmx.org/) for seamless interactivity and [Bootstrap 5](https://getbootstrap.com/) for responsive design.

---

## 🚀 Features

- **Dynamic Patient List** – Instantly browse patients from the FHIR server.
- **Patient Details** – View demographics, contact info, and identifiers.
- **Lab Results** – Interactive, formatted lab data per patient.
- **Medications & Allergies** – See current medications and allergy history.
- **Stats & Insights** – Visualize patient demographics and trends.
- **Profile & Logout** – Manage your session with a click.
- **Smooth Transitions** – No full page reloads, thanks to HTMX.

Additional features added in this repo
- **Settings** to choose a server to pull from
- **PatientSummary** $summary bundles to text area for use in IG examples
- **Diagnostic Requesting** dialog, create an AU eRequesting compliant bundle in the text area
---

## 🛠️ Quickstart

- I have hosted an instance on render so you can see it working (and for Connectathon'ers)

```
https://patient-dashboard-t065.onrender.com/
```

- To clone and run the original Davey Mason code...
```bash
git clone https://github.com/daveymason/Patient-Dashboard-htmx-python-fhir.git
cd Patient-Dashboard-htmx-python-fhir
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
pip install flask requests
python app.py
```
- To clone and run this fork of the repo...
```bash
git clone https://github.com/mjosborne1/Patient-Dashboard
cd Patient-Dashboard
# I use VS Code Create Python environment here, which is essentially...
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# IMPORTANT: BEFORE YOU RUN THE APP
# create a `.env` file in the root folder to contain your FHIR Server credentials (Basic Auth only). See below for an example. 
python app.py
```

- Example `.env` file, all values are fictitious of course
```
FHIR_USERNAME='Tester'
FHIR_PASSWORD='Password4Tester'
FHIR_SERVER='https://yourfhirserver.com/partition/fhir'
```

Visit [http://127.0.0.1:5001/](http://127.0.0.1:5001/) in your browser.

---

## 🤝 Contributing

1. Fork & clone the original [repo](https://github.com/daveymason/Patient-Dashboard-htmx-python-fhir.git)
2. Create a feature branch
3. Commit & push your changes
4. Open a pull request

---

## 📄 License

MIT License. See [LICENSE](LICENSE).

---

## 🙏 Credits

- Logo by [Freepik](https://www.freepik.com/icon/computer_8811410#fromView=search&page=1&position=5&uuid=7f2f0cf5-731f-4ab9-9ab6-1ec888c8328b) (Flaticon)
- Project by [daveymason.com](https://daveymason.com)

---

[Original Project Repository](https://github.com/daveymason/Patient-Dashboard-htmx-python-fhir)


---
    I'd just like to acknowledge Davey Mason for this amazing starter kit. Thanks Davey!!!

    Michael Osborne
